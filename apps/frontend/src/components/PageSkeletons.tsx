import { useLocation } from "react-router-dom";
import { HomeSkeleton } from "./HomeSkeleton";

/**
 * Skeleton di pagina condivisi: riproducono la struttura delle schermate reali
 * (heading, card, righe, form) per evitare il salto di layout al caricamento.
 * Usano solo token (`--bg2`/`--line`) tramite le classi `sk-*` di styles.css.
 */

function SkeletonHeading({
  title,
  eyebrow,
}: {
  title: string;
  eyebrow?: string;
}) {
  return (
    <section className="page-heading">
      <div>
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        <h1>{title}</h1>
      </div>
    </section>
  );
}

function SkeletonLine({
  width,
  tall = false,
}: {
  width: number;
  tall?: boolean;
}) {
  return (
    <span
      className={`skeleton sk-line${tall ? " tall" : ""}`}
      style={{ width: `${width}%` }}
      aria-hidden="true"
    />
  );
}

function SkeletonRows({
  rows,
  avatar = false,
}: {
  rows: number;
  avatar?: boolean;
}) {
  return (
    <div className="sk-rows">
      {Array.from({ length: rows }, (_, index) => (
        <div className="sk-row" key={index}>
          {avatar ? (
            <span className="skeleton sk-avatar" aria-hidden="true" />
          ) : null}
          <SkeletonLine width={avatar ? 52 : 62} />
          <SkeletonLine width={18} />
        </div>
      ))}
    </div>
  );
}

function SkeletonCard({
  rows = 4,
  avatar = false,
  heading = true,
}: {
  rows?: number;
  avatar?: boolean;
  heading?: boolean;
}) {
  return (
    <section className="card">
      {heading ? (
        <div className="card-heading">
          <SkeletonLine width={28} tall />
        </div>
      ) : null}
      <SkeletonRows rows={rows} avatar={avatar} />
    </section>
  );
}

function SkeletonFields({ fields = 3 }: { fields?: number }) {
  return (
    <div className="sk-field-grid">
      {Array.from({ length: fields }, (_, index) => (
        <span className="skeleton sk-field" key={index} aria-hidden="true" />
      ))}
    </div>
  );
}

/** Pagine con form inline + elenco (Conti, Salvadanai). */
function FormListSkeleton({
  title,
  eyebrow,
}: {
  title: string;
  eyebrow: string;
}) {
  return (
    <div className="stack-page" aria-busy="true">
      <SkeletonHeading title={title} eyebrow={eyebrow} />
      <section className="card">
        <SkeletonFields fields={3} />
        <div className="sk-actions">
          <span className="skeleton sk-button" aria-hidden="true" />
        </div>
      </section>
      <SkeletonCard rows={4} avatar />
    </div>
  );
}

/** Pagine con filtri + elenco (Movimenti, Cestino). */
function FilterListSkeleton({
  title,
  eyebrow,
  rows = 5,
}: {
  title: string;
  eyebrow: string;
  rows?: number;
}) {
  return (
    <div className="stack-page" aria-busy="true">
      <SkeletonHeading title={title} eyebrow={eyebrow} />
      <section className="card">
        <div className="sk-filters">
          <span className="skeleton sk-pill" aria-hidden="true" />
          <span className="skeleton sk-pill" aria-hidden="true" />
          <span className="skeleton sk-field" aria-hidden="true" />
          <span className="skeleton sk-field" aria-hidden="true" />
        </div>
      </section>
      <SkeletonCard rows={rows} avatar />
    </div>
  );
}

/** Lista semplice (Automazioni). */
function ListSkeleton({
  title,
  eyebrow,
  cards = 1,
}: {
  title: string;
  eyebrow: string;
  cards?: number;
}) {
  return (
    <div className="stack-page" aria-busy="true">
      <SkeletonHeading title={title} eyebrow={eyebrow} />
      {Array.from({ length: cards }, (_, index) => (
        <SkeletonCard key={index} rows={index === 0 ? 4 : 3} avatar />
      ))}
    </div>
  );
}

/** Investimenti: card riepilogo + elenco posizioni. */
function InvestmentsSkeleton() {
  return (
    <div className="stack-page" aria-busy="true">
      <SkeletonHeading title="Investimenti" eyebrow="Patrimonio" />
      <section className="sk-stat-grid">
        {[0, 1, 2, 3].map((index) => (
          <div className="card" key={index}>
            <SkeletonLine width={55} />
            <span
              className="skeleton sk-line tall sk-stat-value"
              aria-hidden="true"
            />
          </div>
        ))}
      </section>
      <SkeletonCard rows={4} avatar />
    </div>
  );
}

/** Impostazioni/Profilo: sezioni con campi. */
function SettingsSkeleton({ title = "Impostazioni" }: { title?: string }) {
  return (
    <div className="stack-page profile-page" aria-busy="true">
      <SkeletonHeading title={title} />
      <section className="card">
        <div className="sk-filters">
          <span className="skeleton sk-field" aria-hidden="true" />
        </div>
      </section>
      {[0, 1].map((index) => (
        <section className="card" key={index}>
          <div className="card-heading">
            <SkeletonLine width={24} tall />
          </div>
          <SkeletonFields fields={2} />
        </section>
      ))}
    </div>
  );
}

function ProfileSkeleton() {
  return (
    <div className="stack-page profile-page" aria-busy="true">
      <SectionHeroSkeleton />
      {[0, 1].map((index) => (
        <section className="card" key={index}>
          <div className="card-heading">
            <SkeletonLine width={22} tall />
          </div>
          <SkeletonFields fields={2} />
        </section>
      ))}
    </div>
  );
}

function SectionHeroSkeleton() {
  return (
    <section className="card">
      <div className="sk-profile-head">
        <span className="skeleton sk-avatar large" aria-hidden="true" />
        <div className="sk-profile-lines">
          <SkeletonLine width={45} tall />
          <SkeletonLine width={65} />
        </div>
      </div>
    </section>
  );
}

/** Amministrazione: card con tabelle/righe. */
function AdminSkeleton() {
  return (
    <div className="stack-page" aria-busy="true">
      <SkeletonHeading title="Impostazioni globali" />
      {[0, 1, 2].map((index) => (
        <SkeletonCard key={index} rows={index === 0 ? 3 : 2} />
      ))}
    </div>
  );
}

/** Import: area di caricamento + anteprima. */
function ImportSkeleton() {
  return (
    <div className="stack-page" aria-busy="true">
      <SkeletonHeading title="Importa movimenti" eyebrow="Movimenti" />
      <section className="card">
        <span className="skeleton sk-dropzone" aria-hidden="true" />
        <SkeletonFields fields={2} />
        <div className="sk-actions">
          <span className="skeleton sk-button" aria-hidden="true" />
        </div>
      </section>
      <SkeletonCard rows={3} />
    </div>
  );
}

/** Accesso/setup/pending: card stretta centrata. */
function AuthSkeleton() {
  return (
    <div className="sk-auth" aria-busy="true">
      <div className="card narrow">
        <div className="sk-profile-head">
          <span className="skeleton sk-avatar large" aria-hidden="true" />
          <div className="sk-profile-lines">
            <SkeletonLine width={60} tall />
            <SkeletonLine width={80} />
          </div>
        </div>
        <SkeletonFields fields={2} />
        <div className="sk-actions">
          <span className="skeleton sk-button" aria-hidden="true" />
        </div>
      </div>
    </div>
  );
}

function NotFoundSkeleton() {
  return (
    <div className="stack-page" aria-busy="true">
      <SkeletonHeading title="Pagina" />
      <SkeletonCard rows={2} />
    </div>
  );
}

export function MovementsSkeleton() {
  return <FilterListSkeleton title="Movimenti" eyebrow="Registro" rows={5} />;
}

export function AccountsSkeleton() {
  return <FormListSkeleton title="Conti" eyebrow="Patrimonio" />;
}

export function SavingsSkeleton() {
  return <FormListSkeleton title="Salvadanai" eyebrow="Accantonamenti" />;
}

export function AutomationsSkeleton() {
  return (
    <ListSkeleton title="Automazioni" eyebrow="Accantonamenti ricorrenti" cards={2} />
  );
}

export function InvestmentsPageSkeleton() {
  return <InvestmentsSkeleton />;
}

export function TrashSkeleton() {
  return (
    <FilterListSkeleton title="Elementi eliminati" eyebrow="Cestino" rows={4} />
  );
}

export function SettingsPageSkeleton() {
  return <SettingsSkeleton />;
}

export function ProfilePageSkeleton() {
  return <ProfileSkeleton />;
}

export function ImportPageSkeleton() {
  return <ImportSkeleton />;
}

export function AdminPageSkeleton() {
  return <AdminSkeleton />;
}

export function AuthPageSkeleton() {
  return <AuthSkeleton />;
}

export function NotFoundPageSkeleton() {
  return <NotFoundSkeleton />;
}

/**
 * Skeleton del percorso corrente: usato come fallback dei guard di route
 * (setup/auth) così ogni pagina mostra subito la propria forma.
 */
export function RouteSkeleton() {
  const { pathname } = useLocation();
  if (pathname === "/") return <HomeSkeleton />;
  if (pathname === "/movements") return <MovementsSkeleton />;
  if (pathname === "/accounts") return <AccountsSkeleton />;
  if (pathname === "/savings") return <SavingsSkeleton />;
  if (pathname === "/automations") return <AutomationsSkeleton />;
  if (pathname === "/investments") return <InvestmentsPageSkeleton />;
  if (pathname === "/trash") return <TrashSkeleton />;
  if (pathname === "/import") return <ImportPageSkeleton />;
  if (pathname === "/account") return <ProfilePageSkeleton />;
  if (pathname === "/settings") return <SettingsPageSkeleton />;
  if (pathname === "/admin") return <AdminPageSkeleton />;
  if (
    pathname === "/login" ||
    pathname === "/register" ||
    pathname === "/pending" ||
    pathname === "/setup"
  ) {
    return <AuthPageSkeleton />;
  }
  return <NotFoundPageSkeleton />;
}
