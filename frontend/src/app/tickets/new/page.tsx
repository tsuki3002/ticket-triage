"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";

export default function NewTicketPage() {
  const router = useRouter();
  const [customerName, setCustomerName] = useState("");
  const [customerEmail, setCustomerEmail] = useState("");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [productModule, setProductModule] = useState("");
  const [attachmentLink, setAttachmentLink] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [savingMode, setSavingMode] = useState<"save" | "analyze" | null>(null);

  function validate(): boolean {
    const errors: Record<string, string> = {};
    if (!customerName.trim()) errors.customer_name = "Customer name is required.";
    else if (customerName.length > 100) errors.customer_name = "Max 100 characters.";

    if (!customerEmail.trim()) errors.customer_email = "Customer email is required.";
    else if (!/^\S+@\S+\.\S+$/.test(customerEmail)) errors.customer_email = "Enter a valid email.";
    else if (customerEmail.length > 150) errors.customer_email = "Max 150 characters.";

    if (!subject.trim()) errors.subject = "Subject is required.";
    else if (subject.trim().length < 10) errors.subject = "Minimum 10 characters.";
    else if (subject.length > 200) errors.subject = "Max 200 characters.";

    if (!description.trim()) errors.description = "Description is required.";
    else if (description.trim().length < 30) errors.description = "Minimum 30 characters.";

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function handleSave(mode: "save" | "analyze") {
    setSubmitError(null);
    if (!validate()) return;

    setSavingMode(mode);
    try {
      const createRes = await api.post("/tickets", {
        customer_name: customerName.trim(),
        customer_email: customerEmail.trim(),
        subject: subject.trim(),
        description: description.trim(),
        product_module: productModule.trim() || null,
        attachment_link: attachmentLink.trim() || null,
      });

      const ticketId = createRes.data.id;

      if (mode === "save") {
        router.push(`/tickets/${ticketId}`);
        return;
      }

      try {
        await api.post(`/tickets/${ticketId}/analyze`);
      } catch {
        // Ticket already saved above -- AI failure doesn't block navigation.
      }
      router.push(`/tickets/${ticketId}`);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setSubmitError(typeof detail === "string" ? detail : "Could not save the ticket. Please try again.");
    } finally {
      setSavingMode(null);
    }
  }

  function handleCancel() {
    const hasInput = customerName || customerEmail || subject || description || productModule || attachmentLink;
    if (hasInput && !window.confirm("You have unsaved changes. Discard them?")) return;
    router.push("/dashboard");
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4">
        <h1 className="text-lg font-semibold">Create Support Ticket</h1>
      </header>

      <main className="max-w-2xl mx-auto px-6 py-8">
        <div className="bg-white rounded-lg shadow p-6 space-y-5">
          <Field label="Customer Name" error={fieldErrors.customer_name}>
            <input value={customerName} onChange={(e) => setCustomerName(e.target.value)} maxLength={100} className="w-full border rounded px-3 py-2 text-sm" />
          </Field>
          <Field label="Customer Email" error={fieldErrors.customer_email}>
            <input type="email" value={customerEmail} onChange={(e) => setCustomerEmail(e.target.value)} maxLength={150} className="w-full border rounded px-3 py-2 text-sm" />
          </Field>
          <Field label="Subject" error={fieldErrors.subject} hint="10–200 characters">
            <input value={subject} onChange={(e) => setSubject(e.target.value)} maxLength={200} className="w-full border rounded px-3 py-2 text-sm" />
          </Field>
          <Field label="Description" error={fieldErrors.description} hint="Minimum 30 characters">
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={5} className="w-full border rounded px-3 py-2 text-sm" />
          </Field>
          <Field label="Product / Module (optional)">
            <input value={productModule} onChange={(e) => setProductModule(e.target.value)} maxLength={100} placeholder="e.g. Authentication, Billing, Reporting" className="w-full border rounded px-3 py-2 text-sm" />
          </Field>
          <Field label="Attachment Link (optional)">
            <input value={attachmentLink} onChange={(e) => setAttachmentLink(e.target.value)} placeholder="https://..." className="w-full border rounded px-3 py-2 text-sm" />
          </Field>

          {submitError && <p className="text-sm text-red-600">{submitError}</p>}

          <div className="flex gap-3 pt-2">
            <button onClick={() => handleSave("save")} disabled={savingMode !== null} className="bg-gray-800 text-white text-sm font-medium rounded px-4 py-2 hover:bg-gray-900 disabled:opacity-50">
              {savingMode === "save" ? "Saving..." : "Save Ticket"}
            </button>
            <button onClick={() => handleSave("analyze")} disabled={savingMode !== null} className="bg-blue-600 text-white text-sm font-medium rounded px-4 py-2 hover:bg-blue-700 disabled:opacity-50">
              {savingMode === "analyze" ? "Analyzing..." : "Save and Analyze"}
            </button>
            <button onClick={handleCancel} disabled={savingMode !== null} className="text-sm text-gray-500 hover:text-gray-800 px-4 py-2">
              Cancel
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

function Field({ label, error, hint, children }: { label: string; error?: string; hint?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium mb-1">{label}</label>
      {children}
      {error ? <p className="text-xs text-red-600 mt-1">{error}</p> : hint ? <p className="text-xs text-gray-400 mt-1">{hint}</p> : null}
    </div>
  );
}