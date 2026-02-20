"use client";

import { useEffect, useState, createContext, useContext, ReactNode } from "react";
import { toast } from "sonner";

interface AlertNotification {
  type: string;
  event_type: string;
  severity: string;
  description: string;
  timestamp: string;
  camera_index?: number;
  threat_level?: string;
  persons_detected?: number;
  vehicles_detected?: number;
  total_detections?: number;
}

interface NotificationContextType {
  isConnected: boolean;
  lastAlert: AlertNotification | null;
  alertCount: number;
}

const NotificationContext = createContext<NotificationContextType>({
  isConnected: false,
  lastAlert: null,
  alertCount: 0,
});

export function useNotifications() {
  return useContext(NotificationContext);
}

interface NotificationProviderProps {
  children: ReactNode;
}

export function NotificationProvider({ children }: NotificationProviderProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastAlert, setLastAlert] = useState<AlertNotification | null>(null);
  const [alertCount, setAlertCount] = useState(0);

  useEffect(() => {
    // Try multiple URL options
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
    const wsUrl = backendUrl.replace("http://", "ws://").replace("https://", "wss://") + "/ws/alerts";
    
    console.log("🔌 WebSocket URL:", wsUrl);
    
    let ws: WebSocket;
    let reconnectTimeout: NodeJS.Timeout;

    function connect() {
      console.log("🔌 Connecting to alert WebSocket...");
      
      try {
        ws = new WebSocket(wsUrl);
      } catch (err) {
        console.error("❌ Failed to create WebSocket:", err);
        return;
      }

      ws.onopen = () => {
        console.log("✅ WebSocket connected for notifications");
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const alert: AlertNotification = JSON.parse(event.data);
          console.log("📨 Alert received:", alert);
          console.log("📝 Description:", alert.description);
          console.log("⚠️ Severity:", alert.severity);
          
          setLastAlert(alert);
          setAlertCount((prev) => prev + 1);

          // Clean up description - handle undefined/null
          const cleanDescription = alert.description?.toString().replace(/\n/g, " ") || "🎥 Camera Alert";
          console.log("✨ Clean description:", cleanDescription);
          
          // Show toast notification based on severity
          if (alert.severity === "HIGH") {
            toast.error(cleanDescription, {
              duration: 5000,
              icon: "⚠️",
            });
          } else if (alert.severity === "MEDIUM") {
            toast.warning(cleanDescription, {
              duration: 3000,
              icon: "👤",
            });
          } else {
            toast.info(cleanDescription, {
              duration: 2000,
            });
          }
        } catch (error) {
          console.error("❌ Failed to parse alert:", error);
        }
      };

      ws.onclose = () => {
        console.log("🔌 WebSocket disconnected");
        setIsConnected(false);
        
        // Reconnect after 5 seconds
        reconnectTimeout = setTimeout(connect, 5000);
      };

      ws.onerror = (error) => {
        console.error("❌ WebSocket error:", error);
        setIsConnected(false);
      };
    }

    connect();

    return () => {
      if (ws) {
        ws.close();
      }
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
    };
  }, []);

  return (
    <NotificationContext.Provider value={{ isConnected, lastAlert, alertCount }}>
      {children}
    </NotificationContext.Provider>
  );
}
