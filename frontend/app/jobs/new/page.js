"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { api } from "@/lib/api";
import AuthGuard from "@/components/AuthGuard";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";

const schema = z.object({
    pet_id: z.string({ error: "Please select a pet" }).min(1, "Please select a pet"),
    start_date: z.string().min(1, "Start date is required"),
    end_date: z.string().min(1, "End date is required"),
    description: z.string().min(10, "Please provide at least 10 characters"),
    budget: z.preprocess(
        (v) => (v === "" ? undefined : Number(v)),
        z.number().positive("Budget must be positive").optional(),
    ),
});

function NewJobForm() {
    const router = useRouter();
    const [pets, setPets] = useState([]);
    const [petsLoading, setPetsLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [selectedPetId, setSelectedPetId] = useState('');
    const selectedPet = pets.find((p) => p.id === selectedPetId) ?? null;

    const {
        register,
        handleSubmit,
        setValue,
        formState: { errors },
    } = useForm({ resolver: zodResolver(schema) });

    useEffect(() => {
        api.pets
            .list()
            .then(setPets)
            .catch((e) => toast.error(e.message))
            .finally(() => setPetsLoading(false));
    }, []);

    const onSubmit = async (data) => {
        setSaving(true);
        try {
            await api.bookings.create(data);
            toast.success("Job posted!");
            router.push("/dashboard");
        } catch (e) {
            toast.error(e.message);
        } finally {
            setSaving(false);
        }
    };

    if (petsLoading) return <LoadingSkeleton rows={1} />;

    return (
        <div className="max-w-lg mx-auto">
            <Card>
                <CardHeader>
                    <CardTitle>Post a job</CardTitle>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                        <div className="space-y-1">
                            <Label>Pet *</Label>
                            {pets.length === 0 ? (
                                <p className="text-sm text-gray-500">
                                    No pets yet.{" "}
                                    <Link href="/pets/new" className="text-emerald-600 hover:underline">
                                        Add one first.
                                    </Link>
                                </p>
                            ) : (
                                <Select
                                    value={selectedPetId}
                                    onValueChange={(v) => {
                                        setValue("pet_id", v, { shouldValidate: true });
                                        setSelectedPetId(v);
                                    }}
                                >
                                    <SelectTrigger>
                                        <span
                                            data-slot="select-value"
                                            className={`flex flex-1 text-left text-sm${!selectedPet ? " text-muted-foreground" : ""}`}
                                        >
                                            {selectedPet ? `${selectedPet.name} (${selectedPet.species})` : "Select a pet"}
                                        </span>
                                    </SelectTrigger>
                                    <SelectContent>
                                        {pets.map((p) => (
                                            <SelectItem key={p.id} value={p.id} label={`${p.name} (${p.species})`}>
                                                {p.name} ({p.species})
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            )}
                            {errors.pet_id && <p className="text-sm text-red-500">{errors.pet_id.message}</p>}
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-1">
                                <Label htmlFor="start_date">Start date *</Label>
                                <Input id="start_date" type="date" {...register("start_date")} />
                                {errors.start_date && (
                                    <p className="text-sm text-red-500">{errors.start_date.message}</p>
                                )}
                            </div>
                            <div className="space-y-1">
                                <Label htmlFor="end_date">End date *</Label>
                                <Input id="end_date" type="date" {...register("end_date")} />
                                {errors.end_date && <p className="text-sm text-red-500">{errors.end_date.message}</p>}
                            </div>
                        </div>

                        <div className="space-y-1">
                            <Label htmlFor="description">Description *</Label>
                            <Textarea
                                id="description"
                                placeholder="What does your pet need?"
                                {...register("description")}
                            />
                            {errors.description && <p className="text-sm text-red-500">{errors.description.message}</p>}
                        </div>

                        <div className="space-y-1">
                            <Label htmlFor="budget">Budget ($)</Label>
                            <Input id="budget" type="number" step="0.01" {...register("budget")} />
                            {errors.budget && <p className="text-sm text-red-500">{errors.budget.message}</p>}
                        </div>

                        <div className="flex gap-2">
                            <Button
                                type="submit"
                                disabled={saving || pets.length === 0}
                                className="flex-1 bg-emerald-600 hover:bg-emerald-700">
                                {saving ? "Posting…" : "Post job"}
                            </Button>
                            <Button type="button" variant="outline" onClick={() => router.back()}>
                                Cancel
                            </Button>
                        </div>
                    </form>
                </CardContent>
            </Card>
        </div>
    );
}

export default function NewJobPage() {
    return (
        <AuthGuard requiredRole="owner">
            <NewJobForm />
        </AuthGuard>
    );
}
