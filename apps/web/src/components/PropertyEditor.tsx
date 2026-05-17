"use client";

import { useState } from "react";
import { updateProperty, type Property } from "@/lib/api";
import { PROPERTY_TYPE_LABELS, LISTING_TYPE_LABELS, LEGAL_STATUS_LABELS } from "@/lib/utils";

interface Props {
  propertyId: string;
  initialData: Property;
}

export function PropertyEditor({ propertyId, initialData }: Props) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [form, setForm] = useState({
    title_generated: initialData.title_generated || "",
    description_generated: initialData.description_generated || "",
    property_type: initialData.property_type,
    listing_type: initialData.listing_type,
    price: initialData.price ?? "",
    area_sqm: initialData.area_sqm ?? "",
    rooms: initialData.rooms ?? "",
    bedrooms: initialData.bedrooms ?? "",
    bathrooms: initialData.bathrooms ?? "",
    legal_status: initialData.legal_status,
    is_published: initialData.is_published,
    needs_review: initialData.needs_review ?? false,
  });

  const save = async () => {
    setSaving(true);
    try {
      const updates: Record<string, any> = {};
      if (form.title_generated !== initialData.title_generated) updates.title_generated = form.title_generated;
      if (form.description_generated !== initialData.description_generated) updates.description_generated = form.description_generated;
      if (form.property_type !== initialData.property_type) updates.property_type = form.property_type;
      if (form.listing_type !== initialData.listing_type) updates.listing_type = form.listing_type;
      if (form.legal_status !== initialData.legal_status) updates.legal_status = form.legal_status;
      if (Number(form.price) !== initialData.price) updates.price = Number(form.price) || null;
      if (Number(form.area_sqm) !== initialData.area_sqm) updates.area_sqm = Number(form.area_sqm) || null;
      if (Number(form.rooms) !== initialData.rooms) updates.rooms = Number(form.rooms) || null;
      if (Number(form.bedrooms) !== initialData.bedrooms) updates.bedrooms = Number(form.bedrooms) || null;
      if (Number(form.bathrooms) !== initialData.bathrooms) updates.bathrooms = Number(form.bathrooms) || null;
      if (form.is_published !== initialData.is_published) updates.is_published = form.is_published;
      if (form.needs_review !== (initialData.needs_review ?? false)) updates.needs_review = form.needs_review;

      if (Object.keys(updates).length === 0) {
        setMsg("No changes detected");
        setSaving(false);
        return;
      }

      await updateProperty(propertyId, updates);
      setMsg("Property updated! Refresh to see changes.");
      setEditing(false);
    } catch (err) {
      setMsg("Failed to update property");
    }
    setSaving(false);
  };

  if (!editing) {
    return (
      <div className="rounded-xl border border-dashed border-sand-300 bg-sand-50/50 p-4 text-center">
        <button onClick={() => setEditing(true)}
          className="text-sm font-medium text-aqar-500 hover:text-aqar-600">
          ✏️ Edit Property (Admin)
        </button>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-aqar-200 bg-aqar-50/30 p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-sand-900">Edit Property</h2>
        <button onClick={() => setEditing(false)} className="text-sm text-sand-500 hover:text-sand-700">Cancel</button>
      </div>

      {msg && <div className="mb-3 rounded-lg bg-sea-50 border border-sea-200 px-3 py-2 text-sm text-sea-700">{msg}</div>}

      <div className="space-y-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-sand-600">Title</label>
          <input value={form.title_generated} onChange={(e) => setForm({ ...form, title_generated: e.target.value })}
            className="w-full rounded-lg border border-sand-200 px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-sand-600">Description</label>
          <textarea value={form.description_generated} onChange={(e) => setForm({ ...form, description_generated: e.target.value })}
            rows={3} className="w-full rounded-lg border border-sand-200 px-3 py-2 text-sm" />
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-sand-600">Type</label>
            <select value={form.property_type} onChange={(e) => setForm({ ...form, property_type: e.target.value })}
              className="w-full rounded-lg border border-sand-200 px-3 py-2 text-sm">
              {Object.entries(PROPERTY_TYPE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-sand-600">Listing</label>
            <select value={form.listing_type} onChange={(e) => setForm({ ...form, listing_type: e.target.value })}
              className="w-full rounded-lg border border-sand-200 px-3 py-2 text-sm">
              {Object.entries(LISTING_TYPE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-sand-600">Legal Status</label>
            <select value={form.legal_status} onChange={(e) => setForm({ ...form, legal_status: e.target.value })}
              className="w-full rounded-lg border border-sand-200 px-3 py-2 text-sm">
              {Object.entries(LEGAL_STATUS_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-5">
          <div>
            <label className="mb-1 block text-xs font-medium text-sand-600">Price (MAD)</label>
            <input type="number" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })}
              className="w-full rounded-lg border border-sand-200 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-sand-600">Area (m2)</label>
            <input type="number" value={form.area_sqm} onChange={(e) => setForm({ ...form, area_sqm: e.target.value })}
              className="w-full rounded-lg border border-sand-200 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-sand-600">Rooms</label>
            <input type="number" value={form.rooms} onChange={(e) => setForm({ ...form, rooms: e.target.value })}
              className="w-full rounded-lg border border-sand-200 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-sand-600">Bedrooms</label>
            <input type="number" value={form.bedrooms} onChange={(e) => setForm({ ...form, bedrooms: e.target.value })}
              className="w-full rounded-lg border border-sand-200 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-sand-600">Bathrooms</label>
            <input type="number" value={form.bathrooms} onChange={(e) => setForm({ ...form, bathrooms: e.target.value })}
              className="w-full rounded-lg border border-sand-200 px-3 py-2 text-sm" />
          </div>
        </div>
        <div className="flex gap-4">
          <label className="flex items-center gap-2 text-sm text-sand-700">
            <input type="checkbox" checked={form.is_published} onChange={(e) => setForm({ ...form, is_published: e.target.checked })} />
            Published
          </label>
          <label className="flex items-center gap-2 text-sm text-sand-700">
            <input type="checkbox" checked={form.needs_review} onChange={(e) => setForm({ ...form, needs_review: e.target.checked })} />
            Needs Review
          </label>
        </div>
      </div>

      <button onClick={save} disabled={saving}
        className="mt-4 rounded-lg bg-aqar-500 px-6 py-2.5 font-semibold text-white hover:bg-aqar-600 disabled:opacity-50">
        {saving ? "Saving..." : "Save Changes"}
      </button>
    </div>
  );
}
