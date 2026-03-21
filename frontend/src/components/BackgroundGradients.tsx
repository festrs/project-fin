export default function BackgroundGradients() {
  return (
    <div className="fixed top-0 left-0 w-full h-full pointer-events-none -z-10 overflow-hidden">
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
