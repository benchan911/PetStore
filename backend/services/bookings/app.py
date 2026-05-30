import os
import httpx
_orig_httpx_init = httpx.Client.__init__
def _httpx_no_ssl(self, *args, **kwargs):
    kwargs.setdefault('verify', False)
    _orig_httpx_init(self, *args, **kwargs)
httpx.Client.__init__ = _httpx_no_ssl

from flask import Flask, request, jsonify, g
from flask_restful import Api, Resource
from supabase import create_client
from dotenv import load_dotenv
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
from jwt_middleware import jwt_required, role_required
from email_service import send_applicant_confirmed_email, send_applicant_rejected_email

load_dotenv()

app = Flask(__name__)
app.url_map.strict_slashes = False
api = Api(app)

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

class Bookings(Resource):
    @jwt_required
    @role_required('owner')
    def post(self):
        data = request.get_json()
        pet_id = data.get('pet_id')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        description = data.get('description')
        budget = data.get('budget')

        if not all([pet_id, start_date, end_date, description]):
            return {"error": "pet_id, start_date, end_date, description required"}, 400

        # Verify pet belongs to owner
        pet = supabase.table('pets').select('id').eq('id', pet_id).eq('owner_id', g.user_id).execute()
        if not pet.data:
            return {"error": "Pet not found or not owned by you"}, 404

        try:
            booking_data = {
                'owner_id': g.user_id,
                'pet_id': pet_id,
                'start_date': start_date,
                'end_date': end_date,
                'description': description,
                'budget': budget
            }
            result = supabase.table('bookings').insert(booking_data).execute()
            return result.data[0], 201
        except Exception as e:
            return {"error": str(e)}, 400

    @jwt_required
    def get(self):
        try:
            if g.role == 'owner':
                bookings = supabase.table('bookings').select('*, pets(name, species)').eq('owner_id', g.user_id).execute()
            else:  # caretaker
                bookings = supabase.table('bookings').select('*, pets(name, species), profiles!owner_id(name)').eq('status', 'open').execute()
            return bookings.data, 200
        except Exception as e:
            return {"error": str(e)}, 400

class Booking(Resource):
    @jwt_required
    def get(self, booking_id):
        try:
            booking = supabase.table('bookings').select('*, pets(*), applications(*, profiles!caretaker_id(name, email))').eq('id', booking_id).execute()
            if not booking.data:
                return {"error": "Booking not found"}, 404

            # Check permissions
            booking_data = booking.data[0]
            if g.role == 'owner' and booking_data['owner_id'] != g.user_id:
                return {"error": "Not authorized"}, 403

            return booking_data, 200
        except Exception as e:
            return {"error": str(e)}, 400

    @jwt_required
    @role_required('owner')
    def delete(self, booking_id):
        try:
            # Verify ownership and fetch current status
            booking = supabase.table('bookings').select('owner_id, status').eq('id', booking_id).execute()
            if not booking.data or booking.data[0]['owner_id'] != g.user_id:
                return {"error": "Booking not found or not owned by you"}, 404

            current_status = booking.data[0]['status']
            if current_status == 'confirmed':
                return {"error": "Cannot cancel a confirmed booking"}, 400
            if current_status == 'cancelled':
                return {"error": "Booking is already cancelled"}, 400

            supabase.table('bookings').update({'status': 'cancelled'}).eq('id', booking_id).execute()
            return {"message": "Booking cancelled successfully"}, 200
        except Exception as e:
            return {"error": str(e)}, 400

class Apply(Resource):
    @jwt_required
    @role_required('caretaker')
    def post(self, booking_id):
        data = request.get_json()
        message = data.get('message')
        proposed_rate = data.get('proposed_rate')

        try:
            # Check if booking is open
            booking = supabase.table('bookings').select('status').eq('id', booking_id).execute()
            if not booking.data or booking.data[0]['status'] != 'open':
                return {"error": "Booking not available for applications"}, 400

            application_data = {
                'booking_id': booking_id,
                'caretaker_id': g.user_id,
                'message': message,
                'proposed_rate': proposed_rate
            }
            result = supabase.table('applications').insert(application_data).execute()
            return result.data[0], 201
        except Exception as e:
            return {"error": str(e)}, 400

class Confirm(Resource):
    @jwt_required
    @role_required('owner')
    def post(self, booking_id):
        data = request.get_json()
        application_id = data.get('application_id')

        if not application_id:
            return {"error": "application_id required"}, 400

        try:
            # Verify booking ownership
            booking = supabase.table('bookings').select('*, pets(name)').eq('id', booking_id).eq('owner_id', g.user_id).execute()
            if not booking.data:
                return {"error": "Booking not found or not owned by you"}, 404

            booking_data = booking.data[0]

            # Update booking status
            supabase.table('bookings').update({'status': 'confirmed'}).eq('id', booking_id).execute()

            # Update applications
            supabase.table('applications').update({'status': 'accepted'}).eq('id', application_id).execute()
            supabase.table('applications').update({'status': 'rejected'}).eq('booking_id', booking_id).neq('id', application_id).execute()

            # Send emails (best-effort — confirm still succeeds even if email fails)
            try:
                applications = supabase.table('applications').select('*, profiles!caretaker_id(name, email)').eq('booking_id', booking_id).execute()
                for app in applications.data:
                    caretaker_email = (app.get('profiles') or {}).get('email')
                    if not caretaker_email:
                        print(f"[email] skipping app {app['id']}: no caretaker email found", flush=True)
                        continue
                    try:
                        if app['id'] == application_id:
                            send_applicant_confirmed_email(caretaker_email, {
                                'pet_name': booking_data['pets']['name'],
                                'start_date': booking_data['start_date'],
                                'end_date': booking_data['end_date'],
                                'description': booking_data['description']
                            })
                            print(f"[email] confirmation sent to {caretaker_email}", flush=True)
                        else:
                            send_applicant_rejected_email(caretaker_email, {
                                'pet_name': booking_data['pets']['name'],
                                'start_date': booking_data['start_date'],
                                'end_date': booking_data['end_date']
                            })
                            print(f"[email] rejection sent to {caretaker_email}", flush=True)
                    except Exception as email_err:
                        print(f"[email] failed to send to {caretaker_email}: {email_err}", flush=True)
            except Exception as email_err:
                print(f"[email] error fetching applications for emails: {email_err}", flush=True)

            return {"message": "Applicant confirmed successfully"}, 200
        except Exception as e:
            return {"error": str(e)}, 400

class WithdrawApplication(Resource):
    @jwt_required
    @role_required('caretaker')
    def delete(self, booking_id, application_id):
        try:
            application = (
                supabase.table('applications')
                .select('caretaker_id, status')
                .eq('id', application_id)
                .eq('booking_id', booking_id)
                .execute()
            )
            if not application.data or application.data[0]['caretaker_id'] != g.user_id:
                return {"error": "Application not found or not owned by you"}, 404
            if application.data[0]['status'] != 'pending':
                return {"error": f"Cannot withdraw an application with status '{application.data[0]['status']}'"}, 400
            supabase.table('applications').update({'status': 'withdrawn'}).eq('id', application_id).execute()
            return {"message": "Application withdrawn successfully"}, 200
        except Exception as e:
            return {"error": str(e)}, 400


class RejectApplication(Resource):
    @jwt_required
    @role_required('owner')
    def post(self, booking_id, application_id):
        try:
            booking = (
                supabase.table('bookings')
                .select('owner_id, status')
                .eq('id', booking_id)
                .execute()
            )
            if not booking.data or booking.data[0]['owner_id'] != g.user_id:
                return {"error": "Booking not found or not owned by you"}, 404
            if booking.data[0]['status'] != 'open':
                return {"error": "Can only reject applications on open bookings"}, 400
            application = (
                supabase.table('applications')
                .select('status')
                .eq('id', application_id)
                .eq('booking_id', booking_id)
                .execute()
            )
            if not application.data:
                return {"error": "Application not found"}, 404
            if application.data[0]['status'] != 'pending':
                return {"error": f"Cannot reject an application with status '{application.data[0]['status']}'"}, 400
            supabase.table('applications').update({'status': 'rejected'}).eq('id', application_id).execute()
            return {"message": "Application rejected successfully"}, 200
        except Exception as e:
            return {"error": str(e)}, 400


api.add_resource(Bookings, '/bookings')
api.add_resource(Booking, '/bookings/<string:booking_id>')
api.add_resource(Apply, '/bookings/<string:booking_id>/apply')
api.add_resource(Confirm, '/bookings/<string:booking_id>/confirm')
api.add_resource(WithdrawApplication, '/bookings/<string:booking_id>/applications/<string:application_id>')
api.add_resource(RejectApplication, '/bookings/<string:booking_id>/applications/<string:application_id>/reject')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=True)