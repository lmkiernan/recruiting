import { ShortlistProvider } from "./features/shortlists/ShortlistContext";
import { Header } from "./components/layout/Header";
import { DashboardPage } from "./pages/DashboardPage";

export default function App() {
  return (
    <ShortlistProvider>
      <div className="flex flex-col h-screen">
        <Header />
        <DashboardPage />
      </div>
    </ShortlistProvider>
  );
}
