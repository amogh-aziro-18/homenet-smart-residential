import React, { createContext, useContext, useState } from "react";

interface ModeContextType {
  tankViewMode: "latest" | "worst";
  setTankViewMode: React.Dispatch<React.SetStateAction<"latest" | "worst">>;
  pumpViewMode: "latest" | "worst";
  setPumpViewMode: React.Dispatch<React.SetStateAction<"latest" | "worst">>;
}

const ModeContext = createContext<ModeContextType | undefined>(undefined);

export function ModeProvider({ children }: { children: React.ReactNode }) {
  const [tankViewMode, setTankViewMode] = useState<"latest" | "worst">("latest");
  const [pumpViewMode, setPumpViewMode] = useState<"latest" | "worst">("latest");

  return (
    <ModeContext.Provider
      value={{
        tankViewMode,
        setTankViewMode,
        pumpViewMode,
        setPumpViewMode,
      }}
    >
      {children}
    </ModeContext.Provider>
  );
}

export function useMode() {
  const context = useContext(ModeContext);
  if (!context) {
    throw new Error("useMode must be used within ModeProvider");
  }
  return context;
}
