-- CarePets Database Schema
-- Run this in Supabase SQL Editor

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Profiles table (extends auth.users)
CREATE TABLE profiles (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    role TEXT NOT NULL CHECK (role IN ('owner', 'caretaker')),
    name TEXT,
    email TEXT,
    bio TEXT,
    hourly_rate DECIMAL(10,2),
    accepted_pet_types TEXT[], -- e.g., ['dog', 'cat']
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Pets table
CREATE TABLE pets (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    owner_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    name TEXT NOT NULL,
    species TEXT NOT NULL, -- dog, cat, etc.
    breed TEXT,
    age INTEGER,
    notes TEXT,
    photo_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Bookings table
CREATE TABLE bookings (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    owner_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    pet_id UUID REFERENCES pets(id) ON DELETE CASCADE NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    description TEXT NOT NULL,
    budget DECIMAL(10,2),
    status TEXT DEFAULT 'open' CHECK (status IN ('open', 'confirmed', 'cancelled')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Applications table
CREATE TABLE applications (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    booking_id UUID REFERENCES bookings(id) ON DELETE CASCADE NOT NULL,
    caretaker_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    message TEXT,
    proposed_rate DECIMAL(10,2),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected', 'withdrawn')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(booking_id, caretaker_id) -- one application per caretaker per booking
);

-- Row Level Security Policies

-- Profiles: users can read/update their own
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own profile" ON profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile" ON profiles
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Caretakers can view other profiles" ON profiles
    FOR SELECT USING (true); -- allow browsing caretakers

-- Pets: owners can CRUD their own pets
ALTER TABLE pets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Owners can view their own pets" ON pets
    FOR SELECT USING (auth.uid() = owner_id);

CREATE POLICY "Owners can insert their own pets" ON pets
    FOR INSERT WITH CHECK (auth.uid() = owner_id);

CREATE POLICY "Owners can update their own pets" ON pets
    FOR UPDATE USING (auth.uid() = owner_id);

CREATE POLICY "Owners can delete their own pets" ON pets
    FOR DELETE USING (auth.uid() = owner_id);

-- Bookings: owners can CRUD their own, caretakers can view open ones
ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Owners can view their own bookings" ON bookings
    FOR SELECT USING (auth.uid() = owner_id);

CREATE POLICY "Caretakers can view open bookings" ON bookings
    FOR SELECT USING (status = 'open');

CREATE POLICY "Owners can insert their own bookings" ON bookings
    FOR INSERT WITH CHECK (auth.uid() = owner_id);

CREATE POLICY "Owners can update their own bookings" ON bookings
    FOR UPDATE USING (auth.uid() = owner_id);

CREATE POLICY "Owners can delete their own bookings" ON bookings
    FOR DELETE USING (auth.uid() = owner_id);

-- Applications: caretakers can CRUD their own, owners can view for their bookings
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Caretakers can view their own applications" ON applications
    FOR SELECT USING (auth.uid() = caretaker_id);

CREATE POLICY "Owners can view applications for their bookings" ON applications
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM bookings
            WHERE bookings.id = applications.booking_id
            AND bookings.owner_id = auth.uid()
        )
    );

CREATE POLICY "Caretakers can insert their own applications" ON applications
    FOR INSERT WITH CHECK (auth.uid() = caretaker_id);

CREATE POLICY "Caretakers can update their own applications" ON applications
    FOR UPDATE USING (auth.uid() = caretaker_id);

-- Triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pets_updated_at BEFORE UPDATE ON pets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bookings_updated_at BEFORE UPDATE ON bookings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_applications_updated_at BEFORE UPDATE ON applications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();