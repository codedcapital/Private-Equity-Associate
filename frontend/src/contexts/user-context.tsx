"use client";

import React, { createContext, useContext, useState, useCallback } from "react";

export type UserRole = "partner" | "vp" | "associate" | "system";

interface UserContextType {
  userId: string;
  role: UserRole;
  setRole: (role: UserRole) => void;
}

const UserContext = createContext<UserContextType>({
  userId: "dev-user",
  role: "associate",
  setRole: () => {},
});

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [role, setRole] = useState<UserRole>("associate");
  React.useEffect(() => {
    const stored = localStorage.getItem("pe_role");
    if (stored && ["partner", "vp", "associate"].includes(stored)) {
      setRole(stored as UserRole);
    }
  }, []);

  const handleSetRole = useCallback((r: UserRole) => {
    setRole(r);
    localStorage.setItem("pe_role", r);
  }, []);

  return (
    <UserContext.Provider value={{ userId: "dev-user", role, setRole: handleSetRole }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  return useContext(UserContext);
}

export function canViewSection(role: UserRole, section: "investmentView" | "score" | "evidence" | "diligence" | "readiness" | "confidenceBreakdown" | "rawData"): boolean {
  switch (section) {
    case "investmentView":
    case "score":
      return true;
    case "evidence":
      return role !== "partner";
    case "diligence":
      return role !== "partner";
    case "readiness":
      return true;
    case "confidenceBreakdown":
      return role !== "partner";
    case "rawData":
      return role === "associate" || role === "system";
    default:
      return true;
  }
}

export function canEdit(role: UserRole): boolean {
  return role === "associate" || role === "vp" || role === "partner";
}

export function canFinalize(role: UserRole): boolean {
  return role === "vp" || role === "partner";
}

export function canOverrideWeights(role: UserRole): boolean {
  return role === "vp" || role === "partner";
}
