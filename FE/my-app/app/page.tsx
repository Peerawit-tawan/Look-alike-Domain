"use client";

import { FormEvent, useRef, useState } from "react";
import {
  FiGlobe,
  FiImage,
  FiMoreVertical,
  FiSearch,
  FiServer,
  FiShield,
} from "react-icons/fi";
import { ProgressModal } from "./components/ProgressModal";
import { InactiveDomainRow } from "../InactiveDomainRow/page";

type DomainResult = {
  domain: string;
  page_title: string | null;
  dns_a: string[];
  dns_aaaa: string[];
  dns_cname: string[];
  dns_ns: string[];
  dns_mx: string[];
  ip_info: {
    ip: string;
    location: string;
    asn: string;
    asn_type?: string;
  }[];
  http_status: number | null;
  https_status: number | null;
  ssl_info: string | null;
  whois_info: string | null;
  screenshot_url: string | null;
};

type ApiResponse = {
  input_domain: string;
  input_domain_title: string | null;
  input_domain_screenshot: string | null;
  total_generated: number;
  active_count: number;
  inactive_count: number;
  active_domains: DomainResult[];
  inactive_domains: DomainResult[];
};

type ResultTab = "active" | "inactive";

const AVATAR_STYLES = [
  "bg-[#fef2f2] text-[#ef4444]",
  "bg-[#eef2ff] text-[#4f46e5]",
  "bg-[#ecfeff] text-[#0891b2]",
  "bg-[#f0fdf4] text-[#16a34a]",
  "bg-[#fff7ed] text-[#ea580c]",
  "bg-[#f5f3ff] text-[#7c3aed]",
];

function getDomainLabel(domain: string) {
  return domain.replace(/^www\./i, "");
}

function getDomainInitials(domain: string) {
  const primary = getDomainLabel(domain).split(".")[0] || domain;
  return primary.slice(0, 2).toUpperCase();
}

function getAvatarClass(domain: string) {
  const seed = domain.split("").reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return AVATAR_STYLES[seed % AVATAR_STYLES.length];
}

function matchesSearch(item: DomainResult, query: string) {
  if (!query) return true;

  const haystacks = [
    item.domain,
    item.page_title ?? "",
    item.ssl_info ?? "",
    item.whois_info ?? "",
    item.dns_ns.join(" "),
    item.dns_mx.join(" "),
    item.dns_a.join(" "),
    item.ip_info.map((info) => `${info.ip} ${info.location} ${info.asn}`).join(" "),
  ];

  return haystacks.some((value) => value.toLowerCase().includes(query));
}

function MiniBadge({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: "neutral" | "success" | "danger";
}) {
  const toneClass =
    tone === "success"
      ? "bg-[#ecfdf3] text-[#027a48] border-[#c7f0d4]"
      : tone === "danger"
        ? "bg-[#fef3f2] text-[#b42318] border-[#f7d1cc]"
        : "bg-[#f8fafc] text-[#475467] border-[#e4e7ec]";

  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-semibold ${toneClass}`}>
      <span className="uppercase tracking-[0.18em] text-[10px] opacity-70">{label}</span>
      <span>{value}</span>
    </span>
  );
}

function StatusBadge({ code }: { code: number | null }) {
  if (code === null) {
    return <MiniBadge label="HTTP" value="-" />;
  }

  return (
    <MiniBadge
      label="HTTP"
      value={String(code)}
      tone={code >= 200 && code < 300 ? "success" : "danger"}
    />
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-[#eef2f6] py-2.5 last:border-b-0">
      <span className="min-w-24 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#98a2b3]">
        {label}
      </span>
      <span className="text-right text-sm leading-6 text-[#344054]">{value || "-"}</span>
    </div>
  );
}

function DomainCard({
  item,
  apiUrl,
  isActive,
  onImageClick,
}: {
  item: DomainResult;
  apiUrl: string;
  isActive: boolean;
  onImageClick?: (url: string) => void;
}) {
  const httpTone = item.http_status && item.http_status >= 200 && item.http_status < 300 ? "success" : "neutral";
  const httpsTone = item.https_status && item.https_status >= 200 && item.https_status < 300 ? "success" : "neutral";

  return (
    <article className="rounded-[22px] border border-[#e4e7ec] bg-white shadow-[0_16px_40px_rgba(15,23,42,0.05)] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_20px_50px_rgba(15,23,42,0.08)] p-5">
      <div className="flex items-start gap-5">

        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className="truncate text-[15px] font-semibold text-[#101828]">{getDomainLabel(item.domain)}</h3>
              <p className="mt-1 truncate text-sm text-[#667085]">
                {item.page_title || "No page title detected"}
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span
                className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ${isActive ? "bg-[#ecfdf3] text-[#027a48]" : "bg-[#f8fafc] text-[#667085]"
                  }`}
              >
                {isActive ? "ACTIVE" : "INACTIVE"}
              </span>
              <button
                type="button"
                className="rounded-full p-1.5 text-[#98a2b3] transition-colors hover:bg-[#f2f4f7] hover:text-[#344054]"
                aria-label={`More actions for ${item.domain}`}
              >
              </button>
            </div>
          </div>

        </div>
      </div>

      {/* ─── Details panel ─────────────────────────────────────── */}
      <div className="mt-4 rounded-[18px] border border-[#eef2f6] bg-[#fbfcfe] p-3">
        <div className="flex items-start gap-3">

          {/* Screenshot thumbnail — fixed size, never stretches */}
          <div 
            className="h-40 w-48 shrink-0 overflow-hidden rounded-[14px] border border-[#e4e7ec] bg-white cursor-zoom-in group relative"
            onClick={() => item.screenshot_url && onImageClick?.(`${apiUrl}${item.screenshot_url}`)}
          >
            {item.screenshot_url ? (
              <>
                <img
                  src={`${apiUrl}${item.screenshot_url}`}
                  alt={`${item.domain} screenshot`}
                  loading="lazy"
                  decoding="async"
                  className="h-full w-full object-cover object-top transition-transform duration-300 group-hover:scale-105"
                />
                <div className="absolute inset-0 flex items-center justify-center bg-black/0 transition-colors group-hover:bg-black/10">
                   <FiImage className="text-white opacity-0 transition-opacity group-hover:opacity-100 h-6 w-6" />
                </div>
              </>
            ) : (
              <div className="flex h-full flex-col items-center justify-center gap-1 text-[11px] text-[#c4cdd6]">
                <FiImage className="h-4 w-4" />
                <span>No screenshot</span>
              </div>
            )}
          </div>

          {/* Data grid — fills remaining space */}
          <div className="min-w-0 flex-1 grid grid-cols-3 gap-x-4 gap-y-0 divide-x divide-[#eef2f6]">

            {/* Col 1: DNS */}
            <div className="pr-4 space-y-0">
              <div className="mb-1.5 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#98a2b3]">
                <FiServer className="h-3 w-3" /> DNS
              </div>
              {[
                { k: "A", v: item.dns_a.join(", ") },
                // { k: "AAAA", v: item.dns_aaaa.join(", ") },
                // { k: "CNAME", v: item.dns_cname.join(", ") },
                { k: "NS", v: item.dns_ns.join(", ") },
                { k: "MX", v: item.dns_mx.join(", ") },
              ].map(({ k, v }) => (
                <div key={k} className="flex items-start gap-1.5 border-b border-[#f2f4f7] py-1.5 last:border-b-0">
                  <span className="w-10 shrink-0 text-[10px] font-semibold uppercase tracking-wider text-[#c4cdd6]">{k}</span>
                  <span className="break-words text-[11px] text-[#344054]">{v || "-"}</span>
                </div>
              ))}
            </div>

            {/* Col 2: Connection */}
            <div className="px-4 space-y-0">
              <div className="mb-1.5 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#98a2b3]">
                <FiShield className="h-3 w-3" /> Connection
              </div>
              {[
                { k: "HTTP", v: item.http_status ? String(item.http_status) : "-" },
                { k: "HTTPS", v: item.https_status ? String(item.https_status) : "-" },
                { k: "SSL", v: item.ssl_info || "-" },
                { k: "WHOIS", v: item.whois_info || "-" },
              ].map(({ k, v }) => (
                <div key={k} className="flex items-start gap-1.5 border-b border-[#f2f4f7] py-1.5 last:border-b-0">
                  <span className="w-10 shrink-0 text-[10px] font-semibold uppercase tracking-wider text-[#c4cdd6]">{k}</span>
                  <span className="break-words text-[11px] text-[#344054]">{v}</span>
                </div>
              ))}
            </div>

            {/* Col 3: IP Intelligence */}
            <div className="pl-4 space-y-0">
              <div className="mb-1.5 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#98a2b3]">
                <FiGlobe className="h-3 w-3" /> IP Intelligence
              </div>
              {item.ip_info.length === 0 ? (
                <p className="text-[11px] text-[#c4cdd6]">No IP data</p>
              ) : (
                <div className="space-y-2">
                  {item.ip_info.map((info, idx) => (
                    <div key={`${info.ip}-${idx}`} className="rounded-xl border border-[#eef2f6] bg-white p-2">
                      <div className="text-[11px] font-semibold text-[#101828]">{info.ip}</div>
                      <div className="mt-0.5 break-words text-[10px] text-[#667085]">{info.location}</div>
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {info.asn && <span className="rounded-full bg-[#f8fafc] border border-[#e4e7ec] px-1.5 py-0.5 text-[9px] font-semibold text-[#475467]">ASN {info.asn}</span>}
                        {info.asn_type && <span className="rounded-full bg-[#f8fafc] border border-[#e4e7ec] px-1.5 py-0.5 text-[9px] font-semibold uppercase text-[#475467]">{info.asn_type}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

          </div>
        </div>
      </div>

    </article>
  );
}

export default function Home() {
  const [domain, setDomain] = useState("");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ApiResponse | null>(null);
  const [error, setError] = useState("");
  const [resultSearch, setResultSearch] = useState("");
  const [activeTab, setActiveTab] = useState<ResultTab>("active");
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  const cancelledRef = useRef(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const searchTerm = resultSearch.trim().toLowerCase();
  const currentResults = activeTab === "active" ? data?.active_domains ?? [] : data?.inactive_domains ?? [];
  const filteredResults = currentResults.filter((item) => matchesSearch(item, searchTerm));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!domain.trim()) return;

    cancelledRef.current = false;
    setLoading(true);
    setError("");
    setData(null);
    setActiveTab("active");

    try {
      const res = await fetch(`${apiUrl}/api/check-domain`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain }),
      });

      if (!res.ok) throw new Error();

      if (!cancelledRef.current) {
        setData(await res.json());
      }
    } catch {
      if (!cancelledRef.current) {
        setError("Unable to connect to the backend service.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {loading && (
        <ProgressModal
          onCancel={() => {
            cancelledRef.current = true;
            setLoading(false);
          }}
        />
      )}

      <main className="mx-auto max-w-[1380px] px-4 py-6 sm:px-6 lg:px-8">
        <section className="rounded-[30px] border border-white/70 bg-white/90 px-5 py-5 shadow-[0_24px_60px_rgba(15,23,42,0.08)] backdrop-blur-xl sm:px-7">
          <div className="flex flex-col gap-5 border-b border-[#eef2f6] pb-5 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="flex items-center gap-2 text-[33px] font-semibold tracking-tight text-[#101828]">
                <span>Domains</span>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="flex w-full flex-col gap-3 sm:flex-row lg:max-w-[560px]">
              <div className="relative flex-1">
                <FiSearch className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#98a2b3]" />
                <input
                  ref={inputRef}
                  type="text"
                  placeholder="example.com"
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                  disabled={loading}
                  className="h-12 w-full rounded-2xl border border-[#d0d5dd] bg-[#fcfcfd] pl-11 pr-4 text-sm text-[#101828] shadow-sm outline-none transition-all placeholder:text-[#98a2b3] focus:border-[#9db2ff] focus:bg-white focus:ring-4 focus:ring-[#335cff]/10"
                />
              </div>
              <button
                type="submit"
                disabled={loading || !domain.trim()}
                className="inline-flex h-12 items-center justify-center rounded-2xl bg-[#335cff] px-5 text-sm font-semibold text-white shadow-[0_10px_20px_rgba(51,92,255,0.25)] transition-all hover:bg-[#2447d8] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? "Scanning..." : "Scan"}
              </button>
            </form>
          </div>

          {error && (
            <div className="mt-5 rounded-2xl border border-[#fecdca] bg-[#fef3f2] px-4 py-3 text-sm text-[#b42318]">
              {error}
            </div>
          )}

          {data ? (
            <div className="animate-fadeinup">
              <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                {[
                  {
                    label: "Input Domain",
                    value: data.input_domain,
                    subtitle: data.input_domain_title || "Primary scan target",
                  },
                  {
                    label: "Generated",
                    value: data.total_generated.toLocaleString(),
                    subtitle: "Total look-alike candidates",
                  },
                  {
                    label: "Active",
                    value: data.active_count.toLocaleString(),
                    subtitle: "Reachable or delegated domains",
                  },
                  {
                    label: "Inactive",
                    value: data.inactive_count.toLocaleString(),
                    subtitle: "No active web endpoint detected",
                  },
                ].map((item) => (
                  <div key={item.label} className="rounded-[22px] border border-[#e4e7ec] bg-[#fbfcfe] p-4">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#98a2b3]">{item.label}</div>
                    <div className="mt-2 truncate text-xl font-semibold text-[#101828]">{item.value}</div>
                    <div className="mt-1 truncate text-sm text-[#667085]">{item.subtitle}</div>
                  </div>
                ))}
              </div>

              <div className="mt-6 flex flex-col gap-4 border-b border-[#eef2f6] pb-4 lg:flex-row lg:items-center lg:justify-between">
                <div className="flex flex-wrap items-center gap-5 text-sm">
                  <button
                    type="button"
                    onClick={() => setActiveTab("active")}
                    className={`border-b-2 pb-3 font-medium transition-colors ${activeTab === "active"
                      ? "border-[#335cff] text-[#101828]"
                      : "border-transparent text-[#667085] hover:text-[#344054]"
                      }`}
                  >
                    Active Domains <span className="ml-1 text-[#98a2b3]">{data.active_count}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveTab("inactive")}
                    className={`border-b-2 pb-3 font-medium transition-colors ${activeTab === "inactive"
                      ? "border-[#335cff] text-[#101828]"
                      : "border-transparent text-[#667085] hover:text-[#344054]"
                      }`}
                  >
                    Inactive Domains <span className="ml-1 text-[#98a2b3]">{data.inactive_count}</span>
                  </button>
                </div>

                <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                  <div className="relative min-w-[260px] flex-1">
                    <FiSearch className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#98a2b3]" />
                    <input
                      type="text"
                      value={resultSearch}
                      onChange={(e) => setResultSearch(e.target.value)}
                      placeholder="Search results..."
                      className="h-11 w-full rounded-2xl border border-[#d0d5dd] bg-white pl-11 pr-4 text-sm text-[#101828] outline-none transition-all placeholder:text-[#98a2b3] focus:border-[#9db2ff] focus:ring-4 focus:ring-[#335cff]/10"
                    />
                  </div>

                </div>
              </div>

              {(activeTab === "active" && data.active_domains.length < data.active_count) ||
                (activeTab === "inactive" && data.inactive_domains.length < data.inactive_count) ? (
                <div className="mt-4 rounded-2xl border border-[#fedf89] bg-[#fffaeb] px-4 py-3 text-sm text-[#b54708]">
                  Showing the available response set for this scan. Counts above still reflect the full backend totals.
                </div>
              ) : null}

              {filteredResults.length === 0 ? (
                <div className="mt-6 rounded-[24px] border border-dashed border-[#d0d5dd] bg-[#fbfcfe] px-6 py-16 text-center">
                  <div className="text-lg font-semibold text-[#101828]">No domains match this filter</div>
                  <p className="mt-2 text-sm text-[#667085]">
                    Try a different search keyword or switch the result tab.
                  </p>
                </div>
              ) : (
                <div className={`mt-6 grid gap-3 ${activeTab === "inactive" ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3" : "grid-cols-1 gap-4"}`}>
                  {filteredResults.map((item, index) => {
                    const cardKey = `${activeTab}-${item.domain}-${index}`;

                    // 👉 ถ้าเป็น inactive → ใช้แบบเบา
                    if (activeTab === "inactive") {
                      return <InactiveDomainRow key={cardKey} domain={item.domain} />;
                    }

                    // 👉 ถ้าเป็น active → ใช้ของเดิม
                    return (
                      <DomainCard
                        key={cardKey}
                        item={item}
                        apiUrl={apiUrl}
                        isActive={true}
                        onImageClick={setSelectedImage}
                      />
                    );
                  })}
                </div>
              )}
            </div>
          ) : (
            <div className="mt-7 rounded-[28px] border border-dashed border-[#d0d5dd] bg-[#fbfcfe] px-6 py-14">
              <div className="mx-auto max-w-3xl text-center">
                <div className="inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-medium text-[#475467] shadow-sm">
                  <FiSearch className="h-4 w-4 text-[#335cff]" />
                  Ready to inspect look-alike domains
                </div>
                <h2 className="mt-5 text-3xl font-semibold tracking-tight text-[#101828]">
                  Run a scan and review each domain in a dashboard layout
                </h2>
                <p className="mx-auto mt-3 max-w-2xl text-sm leading-7 text-[#667085]">
                  This view keeps the current scanning workflow, but presents the results in a cleaner
                  card-based interface inspired by your reference design.
                </p>

                <div className="mt-8 grid gap-3 text-left md:grid-cols-3">
                  {[
                    {
                      icon: <FiGlobe className="h-5 w-5 text-[#335cff]" />,
                      title: "Scan look-alike domains",
                      body: "Submit a target domain and gather active and inactive permutations in one flow.",
                    },
                    {
                      icon: <FiServer className="h-5 w-5 text-[#335cff]" />,
                      title: "Review technical signals",
                      body: "Inspect DNS, status codes, SSL details, mail servers, and IP intelligence.",
                    },
                    {
                      icon: <FiImage className="h-5 w-5 text-[#335cff]" />,
                      title: "Open rich previews",
                      body: "Expand a card to view screenshots and all the detail blocks for that domain.",
                    },
                  ].map((item) => (
                    <div key={item.title} className="rounded-[22px] border border-[#e4e7ec] bg-white p-5 shadow-sm">
                      <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#eff4ff]">
                        {item.icon}
                      </div>
                      <div className="mt-4 text-base font-semibold text-[#101828]">{item.title}</div>
                      <p className="mt-2 text-sm leading-7 text-[#667085]">{item.body}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </section>
      </main>
      
      {/* ─── Image Lightbox Modal ─────────────────────────────────── */}
      {selectedImage && (
        <div 
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-fadein"
          onClick={() => setSelectedImage(null)}
        >
          <div className="relative max-w-7xl max-h-[90vh] overflow-hidden rounded-3xl shadow-2xl bg-white">
             <button 
                className="absolute top-4 right-4 z-10 bg-black/20 hover:bg-black/40 text-white p-2 rounded-full backdrop-blur-md transition-colors"
                onClick={() => setSelectedImage(null)}
             >
                <FiMoreVertical className="rotate-45 h-6 w-6" />
             </button>
             <img 
                src={selectedImage} 
                alt="Full preview" 
                className="w-full h-full object-contain"
                onClick={(e) => e.stopPropagation()} 
             />
          </div>
        </div>
      )}
    </>
  );
}
