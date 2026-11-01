import { Navigate, Route, Routes } from "react-router-dom";
import { Shell } from "./components/Shell";
import { Admin } from "./pages/Admin";
import { Advisor } from "./pages/Advisor";
import { Budget } from "./pages/Budget";
import { Compare } from "./pages/Compare";
import { DestinationDetail, Destinations } from "./pages/Discover";
import { About, Contact, Privacy, Terms } from "./pages/Info";
import { Landing } from "./pages/Landing";
import { Login } from "./pages/Login";
import { Itinerary, Trips } from "./pages/Plans";
import { Profile } from "./pages/Profile";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route element={<Shell />}>
        <Route path="/destinations" element={<Destinations />} />
        <Route path="/destinations/:slug" element={<DestinationDetail />} />
        <Route path="/advisor" element={<Advisor />} />
        <Route path="/budget" element={<Budget />} />
        <Route path="/compare" element={<Compare />} />
        <Route path="/itinerary" element={<Itinerary />} />
        <Route path="/trips" element={<Trips />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/about" element={<About />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/terms" element={<Terms />} />
        <Route path="/login" element={<Login />} />
        <Route path="/admin" element={<Admin />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
