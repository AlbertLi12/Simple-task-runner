import { useState } from "react";

export type DraftEmail = {
  to: string;
  subject: string;
  body: string;
};

type EmailDraftProps = {
  email: DraftEmail;
};

export default function EmailDraft({ email }: EmailDraftProps) {
  const [draft, setDraft] = useState(email);

  return (
    <section
      aria-label="Email draft"
      className="rounded-lg border border-cyan-200 bg-white p-5 shadow-sm"
    >
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-lg font-semibold">Email draft</h2>
        <span className="rounded-full bg-cyan-50 px-2.5 py-1 text-xs font-medium text-cyan-800">
          Not sent
        </span>
      </div>
      <div className="mt-4 space-y-3 text-sm">
        <div>
          <label
            className="text-xs font-semibold uppercase tracking-wide text-slate-500"
            htmlFor="email-draft-to"
          >
            To
          </label>
          <input
            id="email-draft-to"
            className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 outline-none transition focus:border-cyan-600 focus:ring-2 focus:ring-cyan-100"
            type="email"
            value={draft.to}
            onChange={(event) => setDraft({ ...draft, to: event.target.value })}
          />
        </div>
        <div>
          <label
            className="text-xs font-semibold uppercase tracking-wide text-slate-500"
            htmlFor="email-draft-subject"
          >
            Subject
          </label>
          <input
            id="email-draft-subject"
            className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-950 outline-none transition focus:border-cyan-600 focus:ring-2 focus:ring-cyan-100"
            type="text"
            value={draft.subject}
            onChange={(event) => setDraft({ ...draft, subject: event.target.value })}
          />
        </div>
        <div>
          <label
            className="text-xs font-semibold uppercase tracking-wide text-slate-500"
            htmlFor="email-draft-body"
          >
            Body
          </label>
          <textarea
            id="email-draft-body"
            className="mt-1 min-h-36 w-full resize-y rounded-md border border-slate-300 bg-white px-3 py-2 text-sm leading-6 text-slate-950 outline-none transition focus:border-cyan-600 focus:ring-2 focus:ring-cyan-100"
            value={draft.body}
            onChange={(event) => setDraft({ ...draft, body: event.target.value })}
          />
        </div>
      </div>
    </section>
  );
}
