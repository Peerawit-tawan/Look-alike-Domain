export function InactiveDomainRow({ domain }: { domain: string }) {
  return (
    <div className="flex items-center rounded-xl border border-[#e4e7ec] bg-white px-4 py-3 text-sm shadow-sm">
      <span className="text-[#101828]">{domain}</span>
    </div>
  );
}