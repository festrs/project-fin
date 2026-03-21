export default function BackgroundGradients() {
  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden" aria-hidden="true">
      <div
        className="absolute top-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full blur-[120px]"
        style={{ background: "var(--glass-primary-soft)" }}
      />
      <div
        className="absolute bottom-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full blur-[120px]"
        style={{ background: "var(--glass-positive-soft)" }}
      />
    </div>
  );
}
