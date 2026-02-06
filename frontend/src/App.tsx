import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import DashboardPage from "./pages/DashboardPage";
import ContactsPage from "./pages/ContactsPage";
import ContactDetailPage from "./pages/ContactDetailPage";
import QueuePage from "./pages/QueuePage";
import OpportunitiesPage from "./pages/OpportunitiesPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/contacts" element={<ContactsPage />} />
          <Route path="/contacts/:id" element={<ContactDetailPage />} />
          <Route path="/queue" element={<QueuePage />} />
          <Route path="/opportunities" element={<OpportunitiesPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
