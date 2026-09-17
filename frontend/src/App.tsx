import { useEffect, useState } from "react";
import type { AppUser } from "./api";
import { clearStoredUser, loadStoredUser, storeUser } from "./api";
import Auth from "./components/Auth";
import Chat from "./components/Chat";
import "./App.css";

export default function App() {
  const [user, setUser] = useState<AppUser | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setUser(loadStoredUser());
    setReady(true);
  }, []);

  const handleAuth = (u: AppUser) => {
    storeUser(u);
    setUser(u);
  };

  if (!ready) return null;

  return (
    <main className="app">
      {user ? (
        <Chat
          user={user}
          onLogout={() => {
            clearStoredUser();
            setUser(null);
          }}
        />
      ) : (
        <Auth onAuthenticated={handleAuth} />
      )}
    </main>
  );
}
