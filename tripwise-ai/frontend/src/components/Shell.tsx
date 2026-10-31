import { Compass, MapPin } from "lucide-react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/Auth";

const links = [
  ["/destinations", "Discover"],
  ["/advisor", "Advisor"],
  ["/budget", "Budget"],
  ["/compare", "Compare"],
  ["/itinerary", "Itinerary"],
  ["/trips", "Trips"],
];

export function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2 text-ink">
      <span className="relative grid h-9 w-9 place-items-center rounded-full bg-deep text-cream">
        <Compass size={18} />
        <MapPin size={10} className="absolute -bottom-0.5 -right-0.5 rounded-full bg-teal p-0.5 text-white" />
      </span>
      <span className="font-display text-xl">TripWise</span>
    </Link>
  );
}

export function Shell() {
  const { user, logout } = useAuth();
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-line/80 bg-cream/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3">
          <Logo />
          <nav className="hidden flex-1 items-center gap-1 md:flex">
            {links.map(([to, label]) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `rounded-full px-3 py-1.5 text-sm ${isActive ? "bg-deep text-cream" : "text-ink/80 hover:bg-white"}`
                }
              >
                {label}
              </NavLink>
            ))}
            {user?.role === "admin" && (
              <NavLink to="/admin" className="rounded-full px-3 py-1.5 text-sm text-ink/80 hover:bg-white">
                Admin
              </NavLink>
            )}
          </nav>
          <div className="ml-auto text-sm">
            {user ? (
              <button onClick={logout} className="rounded-full border border-line bg-card px-3 py-1.5">
                {user.name.split(" ")[0]} · Sign out
              </button>
            ) : (
              <Link to="/login" className="rounded-full bg-teal px-3 py-1.5 text-white">
                Sign in
              </Link>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
