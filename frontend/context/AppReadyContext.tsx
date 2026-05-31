"use client";

import { createContext, useContext } from "react";

export const AppReadyContext = createContext(false);

export function useAppReady() {
  return useContext(AppReadyContext);
}
