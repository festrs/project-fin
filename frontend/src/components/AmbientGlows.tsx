export default function AmbientGlows() {
  const baseStyle: React.CSSProperties = {
    position: "fixed",
    width: 600,
    height: 600,
    borderRadius: "50%",
    filter: "blur(120px)",
    pointerEvents: "none",
    zIndex: 0,
  };

  return (
    <>
      <div
        style={{
          ...baseStyle,
          top: -100,
          right: -100,
          background: "var(--blue)",
          opacity: 0.07,
        }}
      />
      <div
        style={{
          ...baseStyle,
          bottom: -200,
          left: -100,
          background: "var(--green)",
          opacity: 0.07,
        }}
      />
      <div
        style={{
          ...baseStyle,
          top: "40%",
          left: "50%",
          background: "var(--purple)",
          opacity: 0.04,
        }}
      />
    </>
  );
}
