import React, { useEffect, useState } from "react";
import api from "../../api/api";
import { formatDateTime } from "../../api/helpers";
import AppShell, { EmptyState } from "../../components/AppShell";

export default function DoctorNotifications() {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api
      .get("/doctor/notifications")
      .then((response) => setNotifications(response.data || []))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const markRead = async (id) => {
    await api.patch(`/doctor/notifications/${id}/read`);
    load();
  };

  return (
    <AppShell role="doctor" title="Notifications">
      <section className="rounded-xl border border-[#e4dfd7] bg-white p-6 shadow-sm">
        <h2 className="text-xl font-bold text-[#061907]">Clinical notifications</h2>
        <div className="mt-5 space-y-3">
          {loading ? (
            <div>Loading notifications...</div>
          ) : notifications.length ? (
            notifications.map((item) => (
              <article key={item.id} className={`rounded-lg border p-4 ${item.is_read ? "border-[#e4dfd7] bg-white" : "border-[#cbdcc7] bg-[#ebf2ec]"}`}>
                <div className="flex flex-col justify-between gap-3 md:flex-row md:items-start">
                  <div>
                    <p className="font-bold text-[#061907]">{item.title}</p>
                    <p className="mt-1 text-sm text-[#667064]">{item.message || "No message provided"}</p>
                    <p className="mt-2 text-xs font-semibold uppercase tracking-wide text-[#667064]">
                      {item.notification_type} • {item.priority} • {formatDateTime(item.created_at)}
                    </p>
                  </div>
                  {!item.is_read && (
                    <button onClick={() => markRead(item.id)} className="rounded-lg bg-[#061907] px-4 py-2 text-sm font-bold text-white">
                      Mark Read
                    </button>
                  )}
                </div>
              </article>
            ))
          ) : (
            <EmptyState title="No notifications" message="Emergency alerts, reviews, and appointments will appear here." />
          )}
        </div>
      </section>
    </AppShell>
  );
}
