import Sidebar from "../components/Sidebar";
import ChatWindow from "../components/ChatWindow";

function Dashboard() {
  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 text-slate-900">
      <Sidebar />
      <ChatWindow />
    </div>
  );
}

export default Dashboard;
