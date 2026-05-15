import Sidebar from "../components/Sidebar";
import ChatWindow from "../components/ChatWindow";

function Dashboard() {
  return (
    <div className="flex h-screen bg-black text-white">
      <Sidebar />
      <ChatWindow />
    </div>
  );
}

export default Dashboard;