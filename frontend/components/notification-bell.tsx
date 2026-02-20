"use client";

import { Bell } from "lucide-react";
import { useNotifications } from "./notification-provider";
import { Button } from "./ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "./ui/tooltip";

export function NotificationBell() {
  const { isConnected, alertCount } = useNotifications();

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          className="h-8 p-1 md:h-fit md:p-2 relative"
          type="button"
          variant="ghost"
        >
          <Bell className={`h-4 w-4 ${isConnected ? "text-green-500" : "text-gray-400"}`} />
          {alertCount > 0 && (
            <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] text-white font-bold">
              {alertCount > 99 ? "99+" : alertCount}
            </span>
          )}
          <span
            className={`absolute bottom-1 right-1 h-2 w-2 rounded-full ${
              isConnected ? "bg-green-500" : "bg-red-500"
            }`}
          />
        </Button>
      </TooltipTrigger>
      <TooltipContent align="end" className="hidden md:block">
        {isConnected ? "Notifications Active" : "Notifications Disconnected"}
      </TooltipContent>
    </Tooltip>
  );
}
