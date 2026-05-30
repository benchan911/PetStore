'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import AuthGuard from '@/components/AuthGuard';
import LoadingSkeleton from '@/components/LoadingSkeleton';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Calendar, DollarSign, CheckCircle, XCircle, Ban } from 'lucide-react';

const applySchema = z.object({
  message: z.string().min(10, 'Please write at least 10 characters'),
  proposed_rate: z.preprocess(
    (v) => (v === '' ? undefined : Number(v)),
    z.number().positive('Rate must be positive').optional()
  ),
});

const statusColors = {
  open: 'bg-green-100 text-green-800',
  confirmed: 'bg-blue-100 text-blue-800',
  cancelled: 'bg-gray-100 text-gray-600',
  pending: 'bg-yellow-100 text-yellow-800',
  accepted: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-700',
  withdrawn: 'bg-gray-100 text-gray-500',
};

function JobDetailContent() {
  const { id } = useParams();
  const { user } = useAuth();
  const [booking, setBooking] = useState(null);
  const [loading, setLoading] = useState(true);
  const [confirming, setConfirming] = useState(null);
  const [applying, setApplying] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [rejecting, setRejecting] = useState(null);
  const [withdrawing, setWithdrawing] = useState(false);

  const { register, handleSubmit, reset, formState: { errors } } = useForm({
    resolver: zodResolver(applySchema),
  });

  useEffect(() => {
    api.bookings.get(id)
      .then(setBooking)
      .catch((e) => toast.error(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const handleConfirm = async (applicationId) => {
    setConfirming(applicationId);
    try {
      await api.bookings.confirm(id, { application_id: applicationId });
      toast.success('Caretaker confirmed! Emails have been sent.');
      const updated = await api.bookings.get(id);
      setBooking(updated);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setConfirming(null);
    }
  };

  const handleCancelBooking = async () => {
    setCancelling(true);
    try {
      await api.bookings.delete(id);
      toast.success('Job posting cancelled.');
      const updated = await api.bookings.get(id);
      setBooking(updated);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setCancelling(false);
    }
  };

  const handleRejectApplication = async (applicationId) => {
    setRejecting(applicationId);
    try {
      await api.bookings.reject(id, applicationId);
      toast.success('Application rejected.');
      const updated = await api.bookings.get(id);
      setBooking(updated);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setRejecting(null);
    }
  };

  const handleWithdraw = async () => {
    if (!myApplication) return;
    setWithdrawing(true);
    try {
      await api.bookings.withdraw(id, myApplication.id);
      toast.success('Application withdrawn.');
      const updated = await api.bookings.get(id);
      setBooking(updated);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setWithdrawing(false);
    }
  };

  const onApply = async (data) => {
    setApplying(true);
    try {
      await api.bookings.apply(id, data);
      toast.success('Application submitted!');
      reset();
      const updated = await api.bookings.get(id);
      setBooking(updated);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setApplying(false);
    }
  };

  if (loading) return <LoadingSkeleton />;
  if (!booking) return <p className="text-gray-500">Booking not found.</p>;

  const myApplication = booking.applications?.find((a) => a.caretaker_id === user?.id);
  const isOwner = user?.role === 'owner';

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Booking details */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <CardTitle>{booking.pets?.name || 'Pet care job'}</CardTitle>
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full capitalize ${statusColors[booking.status]}`}>
              {booking.status}
            </span>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-gray-700">{booking.description}</p>
          <div className="flex gap-4 text-sm text-gray-500">
            <span className="flex items-center gap-1">
              <Calendar className="w-4 h-4" />
              {booking.start_date} → {booking.end_date}
            </span>
            {booking.budget && (
              <span className="flex items-center gap-1">
                <DollarSign className="w-4 h-4" />
                Budget: ${booking.budget}
              </span>
            )}
          </div>
          {booking.pets && (
            <p className="text-sm text-gray-500">
              Species: <span className="capitalize">{booking.pets.species}</span>
              {booking.pets.breed && ` · ${booking.pets.breed}`}
            </p>
          )}
          {isOwner && booking.status === 'open' && (
            <div className="pt-2">
              <Button
                variant="destructive"
                size="sm"
                disabled={cancelling}
                onClick={handleCancelBooking}
              >
                <Ban className="w-3.5 h-3.5 mr-1" />
                {cancelling ? 'Cancelling…' : 'Cancel job posting'}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Owner: applicants list */}
      {isOwner && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Applicants ({booking.applications?.length || 0})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {booking.applications?.length === 0 ? (
              <p className="text-gray-400 text-sm">No applications yet.</p>
            ) : (
              booking.applications.map((app, i) => (
                <div key={app.id}>
                  {i > 0 && <Separator className="mb-4" />}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">
                        {app.profiles?.name || app.profiles?.email || app.caretaker_id}
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${statusColors[app.status]}`}>
                        {app.status}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600">{app.message}</p>
                    {app.proposed_rate && (
                      <p className="text-sm text-gray-500">Proposed rate: ${app.proposed_rate}/hr</p>
                    )}
                    {booking.status === 'open' && app.status === 'pending' && (
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          className="bg-emerald-600 hover:bg-emerald-700"
                          disabled={confirming === app.id || rejecting === app.id}
                          onClick={() => handleConfirm(app.id)}
                        >
                          <CheckCircle className="w-3.5 h-3.5 mr-1" />
                          {confirming === app.id ? 'Confirming…' : 'Confirm this caretaker'}
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          disabled={rejecting === app.id || confirming === app.id}
                          onClick={() => handleRejectApplication(app.id)}
                        >
                          <XCircle className="w-3.5 h-3.5 mr-1" />
                          {rejecting === app.id ? 'Rejecting…' : 'Reject'}
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      )}

      {/* Caretaker: apply form or existing application */}
      {!isOwner && (booking.status === 'open' || myApplication) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              {myApplication ? 'Your application' : 'Apply for this job'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {myApplication ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${statusColors[myApplication.status]}`}>
                    {myApplication.status}
                  </span>
                </div>
                <p className="text-sm text-gray-600">{myApplication.message}</p>
                {myApplication.proposed_rate && (
                  <p className="text-sm text-gray-500">Your rate: ${myApplication.proposed_rate}/hr</p>
                )}
                {myApplication.status === 'pending' && (
                  <Button
                    size="sm"
                    variant="destructive"
                    disabled={withdrawing}
                    onClick={handleWithdraw}
                  >
                    <XCircle className="w-3.5 h-3.5 mr-1" />
                    {withdrawing ? 'Withdrawing…' : 'Withdraw application'}
                  </Button>
                )}
              </div>
            ) : (
              <form onSubmit={handleSubmit(onApply)} className="space-y-4">
                <div className="space-y-1">
                  <Label htmlFor="message">Message *</Label>
                  <Textarea
                    id="message"
                    placeholder="Tell the owner why you're a great fit…"
                    {...register('message')}
                  />
                  {errors.message && <p className="text-sm text-red-500">{errors.message.message}</p>}
                </div>
                <div className="space-y-1">
                  <Label htmlFor="proposed_rate">Your rate ($/hr)</Label>
                  <Input id="proposed_rate" type="number" step="0.01" {...register('proposed_rate')} />
                  {errors.proposed_rate && <p className="text-sm text-red-500">{errors.proposed_rate.message}</p>}
                </div>
                <Button type="submit" disabled={applying} className="w-full bg-emerald-600 hover:bg-emerald-700">
                  {applying ? 'Submitting…' : 'Submit application'}
                </Button>
              </form>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default function JobDetailPage() {
  return (
    <AuthGuard>
      <JobDetailContent />
    </AuthGuard>
  );
}
