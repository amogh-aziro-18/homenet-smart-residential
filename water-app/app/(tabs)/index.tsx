import React, { useEffect, useState, useRef } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Animated,
  TouchableOpacity,
  Modal,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import {
  requestNotificationPermissions,
  sendCriticalWaterAlert,
  sendLowWaterAlert,
  sendPumpFailureRepairAlert,
  sendCombinedWorstCaseAlert,
} from "../../notifications/notifications";
import { useMode } from "../context/ModeContext";
import { API_BASE_URL } from "../../services/api";

export default function Dashboard() {
  const router = useRouter();
  const {
    tankViewMode,
    setTankViewMode,
    pumpViewMode,
    setPumpViewMode,
  } = useMode();
  const [level, setLevel] = useState(0);
  const [status, setStatus] = useState("GOOD");
  const [tasks, setTasks] = useState<any[]>([]);
  const [forecast, setForecast] = useState<any>(null);
  const [notifCount, setNotifCount] = useState(0);
  const [aiSummary, setAiSummary] = useState<string | null>(null);
  const [aiReasoning, setAiReasoning] = useState<string | null>(null);
  const [aiPriority, setAiPriority] = useState<string | null>(null);
  const [aiAction, setAiAction] = useState<string | null>(null);
  const [riskScore, setRiskScore] = useState<number>(0);
  const [riskLevel, setRiskLevel] = useState<string>("LOW");
  const [supervisorAnalysis, setSupervisorAnalysis] = useState<string | null>(null);
  const [showPopup, setShowPopup] = useState(false);
  const [popupTitle, setPopupTitle] = useState("🔔 Alert");
  const [popupBody, setPopupBody] = useState("");
  const [createdTasks, setCreatedTasks] = useState<any[]>([]); // Store created tasks
  const [pumpStatus, setPumpStatus] = useState<any>(null);
  const [assignedTechnician, setAssignedTechnician] = useState<string>("Technician not assigned");
  const waveAnim = useRef(new Animated.Value(0)).current;
  const cardAnim = useRef(new Animated.Value(0)).current;
  /** Previous level after at least one successful API read (avoids spurious pushes on first load). */
  const previousLevelRef = useRef<number | null>(null);
  const lastGoodLevelRef = useRef<number | null>(null);
  const previousPumpIssueRef = useRef<boolean>(false);
  const lastPumpNotifKeyRef = useRef<string>("");
  const lastCombinedNotifKeyRef = useRef<string>("");
  const prevTankViewModeRef = useRef<"latest" | "worst">(tankViewMode);
  const lastTankNotifKeyRef = useRef<string>("");
  const prevPumpViewModeRef = useRef<"latest" | "worst">(pumpViewMode);

  const getStatus = (pct: number) => {
    if (pct < 30) return "LOW";
    if (pct < 70) return "MEDIUM";
    return "GOOD";
  };

  const fetchAll = async () => {
    try {
      const tankRes = await fetch(
        `${API_BASE_URL}/water/run?building_id=BLD_001&mode=latest&tank_mode=${tankViewMode}&pump_mode=${pumpViewMode}`,
        { method: "POST" }
      );
      const tankData = await tankRes.json();

      const tankStatus = tankData?.tank_status;
      const rawPct = tankStatus?.level_percentage;
      const parsedPct =
        typeof rawPct === "number"
          ? rawPct
          : parseFloat(String(rawPct ?? ""));
      const tankValid =
        tankRes.ok &&
        tankStatus &&
        Number.isFinite(parsedPct);

      if (!tankValid) {
        console.warn("🔴 Bad tank response; keeping last known level if any");
        if (lastGoodLevelRef.current != null) {
          setLevel(lastGoodLevelRef.current);
        }
      } else {
        setAiSummary(tankData.ai_summary || null);
        setAiReasoning(tankData.ai_reasoning || null);
        setAiPriority(tankData.ai_priority || null);
        setAiAction(tankData.ai_action || null);
        setCreatedTasks(tankData.created_tasks || []); // Capture created tasks

        // ✅ Get LangGraph results from /water/run response
        if (tankData.langgraph) {
          setSupervisorAnalysis(tankData.langgraph.supervisor_analysis);
          const mergedRiskScore =
            typeof tankData?.maintenance?.risk_score === "number"
              ? tankData.maintenance.risk_score
              : (tankData.langgraph.maintenance_risk_score || 0);
          const mergedRiskLevel =
            tankData?.maintenance?.risk_level ||
            tankData.langgraph.maintenance_risk_level ||
            "LOW";
          setRiskScore(mergedRiskScore);
          setRiskLevel(mergedRiskLevel);
        }

        setPumpStatus(tankData.pump_status || null);
        const currentAlerts = Array.isArray(tankData.alerts) ? tankData.alerts : [];
        const pumpAlert = currentAlerts.find((a: any) => a?.asset === "PUMP");
        const routedAssignment = tankData?.technician_assignment || null;
        const routedTech =
          routedAssignment?.technician_name ||
          tankData?.langgraph?.routing_assignments?.[0]?.technician_name;
        setAssignedTechnician(
          pumpAlert?.details?.technician_name ||
            routedTech ||
            "Technician assignment pending"
        );
        const pct = parsedPct;
        const levelState = String(tankStatus.level_state || "");
        const tankId = String(tankStatus.tank_id || "TANK");

        lastGoodLevelRef.current = pct;
        setLevel(pct);
        setStatus(getStatus(pct));
        setForecast(tankData.forecast);

        // 🔔 Local push: only after first successful sync, when level drops into band
        if (previousLevelRef.current != null) {
          if (levelState === "CRITICAL" && previousLevelRef.current > pct) {
            await sendCriticalWaterAlert(tankId, pct);
          } else if (levelState === "LOW" && previousLevelRef.current > pct) {
            await sendLowWaterAlert(tankId, pct);
          }
        }
        const tankNotifKey = `${tankId}|${levelState}|${pct.toFixed(1)}`;
        const tankWorstJustEnabled =
          prevTankViewModeRef.current !== "worst" && tankViewMode === "worst";
        if (
          tankWorstJustEnabled &&
          (levelState === "LOW" || levelState === "CRITICAL") &&
          lastTankNotifKeyRef.current !== tankNotifKey
        ) {
          if (levelState === "CRITICAL") {
            await sendCriticalWaterAlert(tankId, pct);
          } else {
            await sendLowWaterAlert(tankId, pct);
          }
          lastTankNotifKeyRef.current = tankNotifKey;
        }
        prevTankViewModeRef.current = tankViewMode;
        previousLevelRef.current = pct;

        // 🔔 Pump predictive push in worst-case view (with technician + refill guidance).
        const pump = tankData?.pump_status || {};
        const pumpSignals = pump?.signals || {};
        const maintenanceRiskLevel = String(
          tankData?.maintenance?.risk_level || tankData?.langgraph?.maintenance_risk_level || "LOW"
        ).toUpperCase();
        const pumpHasIssue =
          !!pumpSignals.high_vibration ||
          !!pumpSignals.high_temperature ||
          !!pumpSignals.low_pressure ||
          !!pumpSignals.low_flow ||
          maintenanceRiskLevel === "HIGH" ||
          maintenanceRiskLevel === "CRITICAL";
        const pumpAlertForNotif = currentAlerts.find((a: any) => a?.asset === "PUMP");
        const techName =
          tankData?.technician_assignment?.technician_name ||
          pumpAlertForNotif?.details?.technician_name ||
          tankData?.langgraph?.routing_assignments?.[0]?.technician_name ||
          "Assigned technician";
        const pumpId = String(pump?.pump_id || "PUMP");
        const telemetry = pump?.telemetry || {};
        const notifKey = [
          pumpId,
          techName,
          Number(telemetry?.vibration_mm_s ?? 0).toFixed(1),
          Number(telemetry?.temperature_celsius ?? 0).toFixed(1),
          Number(telemetry?.pressure_psi ?? 0).toFixed(1),
          maintenanceRiskLevel,
        ].join("|");

        const shouldPushPump =
          pumpViewMode === "worst" &&
          (!previousPumpIssueRef.current || lastPumpNotifKeyRef.current !== notifKey);
        if (shouldPushPump) {
          const includeRefill = pct < 30 || tankViewMode === "worst";
          await sendPumpFailureRepairAlert(pumpId, techName, includeRefill);
          lastPumpNotifKeyRef.current = notifKey;
        }

        // Explicit notification when user turns ON pump worst-case toggle.
        // This guarantees a user-visible push similar to water-level worst-case behavior.
        const pumpWorstJustEnabled =
          prevPumpViewModeRef.current !== "worst" &&
          pumpViewMode === "worst";
        if (pumpWorstJustEnabled && lastPumpNotifKeyRef.current !== notifKey) {
          await sendPumpFailureRepairAlert(pumpId, techName, true);
          lastPumpNotifKeyRef.current = notifKey;
        }
        prevPumpViewModeRef.current = pumpViewMode;

        // Combined push when both worst-case toggles are active and both risks exist.
        const combinedRisk = tankViewMode === "worst" && pumpViewMode === "worst" && pct < 30 && pumpHasIssue;
        const combinedKey = `${tankId}|${pumpId}|${techName}|${pct.toFixed(1)}|${notifKey}`;
        if (combinedRisk && lastCombinedNotifKeyRef.current !== combinedKey) {
          await sendCombinedWorstCaseAlert(tankId, pumpId, techName);
          lastCombinedNotifKeyRef.current = combinedKey;
        }
        previousPumpIssueRef.current = pumpHasIssue;
      }

      const taskRes = await fetch(`${API_BASE_URL}/tasks`);
      const taskData = await taskRes.json();
      setTasks(Array.isArray(taskData) ? taskData : [taskData]);

      const notifRes = await fetch(`${API_BASE_URL}/notifications`);
      const notifData = await notifRes.json();
      const notifs = Array.isArray(notifData)
        ? notifData
        : [notifData];

      setNotifCount(notifs.filter((n) => !n.read).length);
    } catch (e) {
      console.error("🔴 API Error:", e);
      console.log("API_BASE_URL:", API_BASE_URL);
    }
  };

  useEffect(() => {
    // Request notification permissions on app load
    requestNotificationPermissions();

    fetchAll();
    const i = setInterval(fetchAll, 20000);  // ✅ Refresh every 20 seconds

    Animated.loop(
      Animated.sequence([
        Animated.timing(waveAnim, {
          toValue: 8,
          duration: 1500,
          useNativeDriver: false,
        }),
        Animated.timing(waveAnim, {
          toValue: 0,
          duration: 1500,
          useNativeDriver: false,
        }),
      ])
    ).start();
    Animated.timing(cardAnim, {
      toValue: 1,
      duration: 450,
      useNativeDriver: true,
    }).start();

    return () => clearInterval(i);
  }, [tankViewMode, pumpViewMode]);

  const statusColor =
    status === "LOW"
      ? "#ef4444"
      : status === "MEDIUM"
      ? "#f59e0b"
      : "#22c55e";

  // Water color matches status
  const waterColor =
    status === "LOW"
      ? "#dc2626"  // Dark red for critical
      : status === "MEDIUM"
      ? "#f97316"  // Orange for medium
      : "#2563eb"; // Blue for good

  const glow =
    status === "LOW"
      ? { shadowColor: "#ef4444", shadowRadius: 20, shadowOpacity: 0.9 }
      : {};

  const pumpSignals = pumpStatus?.signals || {};
  const hasPumpIssue =
    !!pumpSignals.high_vibration ||
    !!pumpSignals.high_temperature ||
    !!pumpSignals.low_pressure ||
    !!pumpSignals.low_flow;
  const tankActionText =
    level < 20
      ? "Refill scheduled. Turn ON the motor immediately."
      : level < 30
      ? "Turn ON the motor and monitor level."
      : "System stable. Keep monitoring.";
  const pumpSummaryLevel = String(riskLevel || pumpStatus?.condition || "LOW").toUpperCase();
  const pumpBadgeColor =
    pumpSummaryLevel === "CRITICAL"
      ? "#ef4444"
      : pumpSummaryLevel === "HIGH"
      ? "#f59e0b"
      : pumpSummaryLevel === "MEDIUM"
      ? "#eab308"
      : "#22c55e";
  const allVisibleTasks = [...createdTasks, ...tasks];
  const topTask =
    allVisibleTasks.sort((a, b) => {
      const order: Record<string, number> = {
        CRITICAL: 4,
        HIGH: 3,
        MEDIUM: 2,
        LOW: 1,
      };
      const prio = (order[b?.priority] || 0) - (order[a?.priority] || 0);
      if (prio !== 0) return prio;
      const bt = new Date(b?.created_at || 0).getTime();
      const at = new Date(a?.created_at || 0).getTime();
      return bt - at;
    })[0] || null;

  return (
    <LinearGradient
      colors={["#0ea5e9", "#e0f2fe"]}
      style={{ flex: 1 }}
    >
      <ScrollView contentContainerStyle={styles.container}>
        {/* HEADER */}
        <View style={styles.header}>
          <Text style={styles.mainTitle}>HOMENET - Water Management System </Text>

          <TouchableOpacity
            onPress={() => router.push("/(tabs)/notifications")}
            style={{ position: "relative" }}
          >
            <Ionicons name="notifications" size={28} color="white" />
            {notifCount > 0 && (
              <View style={styles.badge}>
                <Text style={styles.badgeText}>
                  {notifCount}
                </Text>
              </View>
            )}
          </TouchableOpacity>
        </View>

        {/* VIEW TOGGLES (data-view only: tank / pump worst-case snapshots) */}
        <View style={styles.modeToggle}>
          <TouchableOpacity
            style={[styles.modeBtn, tankViewMode === "worst" && styles.modeBtnActive]}
            onPress={async () => {
              const nextMode = tankViewMode === "latest" ? "worst" : "latest";
              setTankViewMode(nextMode);
              if (nextMode === "worst") {
                const tankId = "TANK";
                // Always notify on worst toggle ON (restores previously expected behavior).
                if (level < 30) {
                  if (level < 20) {
                    await sendCriticalWaterAlert(tankId, level);
                    setPopupTitle("🚨 Tank Critical Level");
                    setPopupBody(
                      "Predictive system detected critical tank risk. Please turn ON the motor immediately and arrange refill support."
                    );
                  } else {
                    await sendLowWaterAlert(tankId, level);
                    setPopupTitle("⚠️ Tank Low Level");
                    setPopupBody(
                      "Predictive system detected low tank level. Please turn ON the motor and schedule refill soon."
                    );
                  }
                } else {
                  await sendLowWaterAlert(tankId, level);
                  setPopupTitle("⚠️ Tank Action");
                  setPopupBody(
                    "Predictive system suggests preventive action. Please turn ON the motor and monitor tank level."
                  );
                }
                // Combined popup when both worst modes are ON.
                if (pumpViewMode === "worst") {
                  const pumpId = String(pumpStatus?.pump_id || "PUMP");
                  const techName = assignedTechnician || "a technician";
                  setPopupTitle("🚨 Combined Emergency Scenario");
                  setPopupBody(
                    `Predictive system indicates combined tank and pump risk. Pump ${pumpId} is under failure-risk workflow and ${techName} is being assigned. Please turn ON motor backup and store water for the next few hours.`
                  );
                }
                setShowPopup(true);
              }
            }}
          >
            <Text style={[styles.modeBtnText, tankViewMode === "worst" && styles.modeBtnTextActive]}>
              Tank Worst Case: {tankViewMode === "worst" ? "ON" : "OFF"}
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.modeBtn, pumpViewMode === "worst" && styles.modeBtnActive]}
            onPress={async () => {
              const nextMode = pumpViewMode === "latest" ? "worst" : "latest";
              setPumpViewMode(nextMode);
              if (nextMode === "worst") {
                const pumpId = String(pumpStatus?.pump_id || "PUMP");
                const techName = assignedTechnician || "a technician";
                await sendPumpFailureRepairAlert(pumpId, techName, true);
                setPopupTitle("🛠️ Pump Failure Risk");
                setPopupBody(
                  `Predictive system indicates pump failure risk for ${pumpId}. ${techName} is being assigned for inspection. Please store water for the next few hours.`
                );
                // Combined popup when both worst modes are ON.
                if (tankViewMode === "worst") {
                  setPopupTitle("🚨 Combined Emergency Scenario");
                  setPopupBody(
                    `Predictive system indicates combined tank and pump risk. Pump ${pumpId} is under failure-risk workflow and ${techName} is being assigned. Please turn ON motor backup and store water for the next few hours.`
                  );
                }
                setShowPopup(true);
              }
            }}
          >
            <Text style={[styles.modeBtnText, pumpViewMode === "worst" && styles.modeBtnTextActive]}>
              Pump Worst Case: {pumpViewMode === "worst" ? "ON" : "OFF"}
            </Text>
          </TouchableOpacity>
        </View>

        <Text style={styles.sectionTitle}>Water Level</Text>

        {/* TANK */}
        <View style={[styles.tank, glow]}>
          <Animated.View
            style={[
              styles.water,
              {
                height: `${level}%`,
                backgroundColor: waterColor,
                transform: [{ translateY: waveAnim }],
              },
            ]}
          />

          <View style={styles.tankText}>
            <Text style={styles.percent}>
              {level.toFixed(1)}%
            </Text>
            <Text style={[styles.status, { color: statusColor }]}>
              {status}
            </Text>
          </View>
        </View>

        {/* 🤖 REAL LANGGRAPH SUMMARY */}
        {(supervisorAnalysis || aiSummary) && (
          <Animated.View style={[styles.analysisCard, { opacity: cardAnim, transform: [{ translateY: cardAnim.interpolate({ inputRange: [0, 1], outputRange: [10, 0] }) }] }]}>
            <View style={styles.analysisHeader}>
              <Text style={styles.analysisTitle}>🤖 AI Assessment</Text>
              <View style={[styles.riskBadge, {
                backgroundColor: riskLevel === "CRITICAL" ? "#ef4444" :
                                riskLevel === "HIGH" ? "#f59e0b" :
                                riskLevel === "MEDIUM" ? "#eab308" : "#22c55e"
              }]}>
                <Text style={styles.riskBadgeText}>
                  {(riskScore * 100).toFixed(0)}% Risk
                </Text>
              </View>
            </View>
            <Text style={styles.analysisText}>{aiSummary || supervisorAnalysis}</Text>
            {!!aiPriority && !!aiAction && (
              <Text style={styles.cardSubtitle}>Priority: {aiPriority} | Action: {aiAction}</Text>
            )}
          </Animated.View>
        )}

        {/* PUMP STATUS CARD */}
        {pumpStatus && (
          <Animated.View style={[styles.card, { opacity: cardAnim }]}>
            <Text style={styles.cardTitle}>Pump Health Summary</Text>
            <Text>ID: {pumpStatus.pump_id}</Text>
            <View style={[styles.riskBadge, { backgroundColor: pumpBadgeColor, alignSelf: "flex-start", marginTop: 8 }]}>
              <Text style={styles.riskBadgeText}>{pumpSummaryLevel}</Text>
            </View>
            <Text style={styles.cardSubtitle}>Technician Assignment</Text>
            <Text style={{ fontWeight: "600", color: hasPumpIssue ? "#b45309" : "#374151" }}>
              {hasPumpIssue ? `${assignedTechnician} assigned for pump inspection` : "No technician needed"}
            </Text>
          </Animated.View>
        )}

        {/* TASK CARD */}
        {topTask && (
          <Animated.View style={[styles.card, { opacity: cardAnim }]}>
            <Text style={styles.cardTitle}>Top Priority Task</Text>
            <Text>{topTask.title}</Text>
            <Text>Priority: {topTask.priority}</Text>
            <Text>Status: {topTask.status || "OPEN"}</Text>
          </Animated.View>
        )}
        <Animated.View style={[styles.card, { opacity: cardAnim }]}>
          <Text style={styles.cardTitle}>Tank Action</Text>
          <Text>{tankActionText}</Text>
        </Animated.View>
      </ScrollView>
      <Modal
        visible={showPopup}
        transparent
        animationType="fade"
        onRequestClose={() => setShowPopup(false)}
      >
        <View style={styles.alertOverlay}>
          <View style={styles.alertBox}>
            <Text style={styles.alertTitle}>{popupTitle}</Text>
            <Text style={styles.alertText}>{popupBody}</Text>
            <TouchableOpacity style={styles.alertCloseBtn} onPress={() => setShowPopup(false)}>
              <Text style={styles.alertCloseBtnText}>OK</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    alignItems: "center",
    paddingTop: 60,
  },

  header: {
    width: "90%",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  mainTitle: {
    fontSize: 34,
    fontWeight: "bold",
    color: "white",
  },

  badge: {
    position: "absolute",
    right: -6,
    top: -6,
    backgroundColor: "red",
    borderRadius: 10,
    paddingHorizontal: 5,
  },

  badgeText: {
    color: "white",
    fontSize: 12,
  },

  sectionTitle: {
    fontSize: 18,
    marginVertical: 10,
    fontWeight: "600",
    color: "white",
  },

  tank: {
    width: 140,
    height: 260,
    borderWidth: 3,
    borderColor: "white",
    borderRadius: 30,
    overflow: "hidden",
    justifyContent: "flex-end",
    backgroundColor: "#e5e7eb", // Light gray background
    marginBottom: 20,
  },

  water: {
    width: "100%",
  },

  tankText: {
    position: "absolute",
    alignSelf: "center",
    top: "40%",
  },

  percent: {
    fontSize: 26,
    fontWeight: "bold",
    textAlign: "center",
    color: "black",
  },

  status: {
    fontSize: 18,
    fontWeight: "bold",
    textAlign: "center",
  },

  card: {
    width: "90%",
    backgroundColor: "white",
    padding: 15,
    borderRadius: 15,
    marginBottom: 15,
  },

  cardTitle: {
    fontSize: 16,
    fontWeight: "bold",
    marginBottom: 5,
  },

  cardSubtitle: {
    fontSize: 13,
    fontWeight: "600",
    marginTop: 8,
    marginBottom: 3,
    color: "#555",
  },

  // New Analysis Card Styles
  analysisCard: {
    width: "90%",
    backgroundColor: "rgba(255, 255, 255, 0.95)",
    padding: 15,
    borderRadius: 15,
    marginBottom: 15,
    borderLeftWidth: 4,
    borderLeftColor: "#3b82f6",
  },

  analysisHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 10,
  },

  analysisTitle: {
    fontSize: 16,
    fontWeight: "bold",
    color: "#111",
  },

  riskBadge: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
  },

  riskBadgeText: {
    color: "white",
    fontWeight: "700",
    fontSize: 12,
  },

  analysisText: {
    fontSize: 13,
    color: "#333",
    lineHeight: 20,
  },

  modeToggle: {
    flexDirection: "row",
    marginVertical: 10,
    gap: 10,
  },

  modeBtn: {
    paddingHorizontal: 15,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: "rgba(255, 255, 255, 0.3)",
    borderWidth: 2,
    borderColor: "rgba(255, 255, 255, 0.5)",
  },

  modeBtnActive: {
    backgroundColor: "white",
    borderColor: "white",
  },

  modeBtnText: {
    fontSize: 14,
    fontWeight: "600",
    color: "white",
  },

  modeBtnTextActive: {
    color: "#0ea5e9",
  },

  // Alert Modal Styles
  alertOverlay: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.7)",
    justifyContent: "center",
    alignItems: "center",
  },

  alertBox: {
    width: "85%",
    backgroundColor: "#fff",
    borderRadius: 20,
    padding: 25,
    borderWidth: 3,
    borderColor: "#ef4444",
    shadowColor: "#ef4444",
    shadowOpacity: 0.8,
    shadowRadius: 15,
    elevation: 10,
  },

  alertTitle: {
    fontSize: 24,
    fontWeight: "bold",
    color: "#ef4444",
    marginBottom: 10,
    textAlign: "center",
  },

  alertText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#333",
    marginBottom: 8,
    textAlign: "center",
  },

  alertLevel: {
    fontSize: 20,
    fontWeight: "bold",
    color: "#dc2626",
    textAlign: "center",
    marginBottom: 12,
    backgroundColor: "#fee2e2",
    paddingVertical: 8,
    borderRadius: 8,
  },

  alertMessage: {
    fontSize: 13,
    color: "#666",
    lineHeight: 20,
    marginBottom: 15,
    fontStyle: "italic",
    backgroundColor: "#f5f5f5",
    padding: 10,
    borderRadius: 8,
  },

  alertTasksSection: {
    backgroundColor: "#fef2f2",
    borderLeftWidth: 4,
    borderLeftColor: "#ef4444",
    padding: 12,
    marginBottom: 15,
    borderRadius: 8,
  },

  alertSubtitle: {
    fontSize: 13,
    fontWeight: "bold",
    color: "#dc2626",
    marginBottom: 8,
  },

  alertTaskItem: {
    fontSize: 12,
    color: "#333",
    marginVertical: 4,
  },

  alertCloseBtn: {
    backgroundColor: "#ef4444",
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: "center",
  },

  alertCloseBtnText: {
    color: "white",
    fontSize: 16,
    fontWeight: "bold",
  },
});
