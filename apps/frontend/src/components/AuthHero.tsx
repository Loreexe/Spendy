export function AuthHero({ glow = false }: { glow?: boolean }) {
  return (
    <div className="auth-hero">
      <img
        className={
          "auth-logo auth-logo-dark" + (glow ? " auth-logo-glow" : "")
        }
        src="/logo/spendy-lockup-h-black-on-dark.svg"
        alt="Spendy"
      />
      <img
        className="auth-logo auth-logo-light"
        src="/logo/spendy-lockup-h-black-on-light.svg"
        alt=""
        aria-hidden="true"
      />
    </div>
  );
}
