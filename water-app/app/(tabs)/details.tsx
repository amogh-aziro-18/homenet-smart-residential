import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Dimensions,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { useMode } from "../context/ModeContext";
import { API_BASE_URL } from "../../services/api";

interface AgentAnalysis {
  status: string;
  supervisor_analysis: string;
  maintenance_risk_score: number;
  maintenance_risk_level: string;
  routing_assignments: any[];
  messages?: string[];
}

export default function Details() {
  const { tankViewMode, pumpViewMode } = useMode();
  const [waterData, setWaterData] = useState<any>(null);
  const [forecast, setForecast] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [agentAnalysis, setAgentAnalysis] = useState<AgentAnalysis | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      console.log("📊 Details: Loading (tank_mode / pump_mode)");

      // Fetch water + agent analysis with SAME view modes as Dashboard
      const waterRes = await fetch(
        `${API_BASE_URL}/water/run?building_id=BLD_001&mode=latest&tank_mode=${tankViewMode}&pump_mode=${pumpViewMode}`,
        { method: "POST" }
      );
      const waterData = await waterRes.json();
      const tankPct = waterData?.tank_status?.level_percentage;
      console.log("💧 Water data:", tankPct + "%");
      setWaterData(waterData);

      // Extract LangGraph analysis (already includes real supervisor_analysis)
      if (waterData?.langgraph) {
        setAgentAnalysis(waterData.langgraph);
      }

      // Keep details aligned with dashboard/orchestrator by using the same forecast payload.
      setForecast(waterData?.forecast || null);
      console.log("📈 Forecast demand level:", waterData?.forecast?.demand_level);

      console.log("✅ Details loaded successfully with tank level:", tankPct);
    } catch (e) {
      console.error("❌ Failed to load details:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [tankViewMode, pumpViewMode]);

  const getRiskColor = (riskLevel: string) => {
    if (riskLevel === "CRITICAL") return "#ef4444";
    if (riskLevel === "HIGH") return "#f59e0b";
    if (riskLevel === "MEDIUM") return "#eab308";
    return "#22c55e";
  };

  const maintenance = waterData?.maintenance;
  const maintenanceSignals = maintenance?.signals || {};
  const routedTechnician = waterData?.technician_assignment || null;
  const maintenanceRiskLevel = maintenance?.risk_level || agentAnalysis?.maintenance_risk_level || "LOW";
  const maintenanceRiskScore =
    typeof maintenance?.risk_score === "number"
      ? maintenance.risk_score
      : (agentAnalysis?.maintenance_risk_score || 0);
  const latestPumpAlert =
    Array.isArray(waterData?.alerts)
      ? [...waterData.alerts]
          .reverse()
          .find(
            (a: any) =>
              a?.asset === "PUMP" ||
              a?.category === "PUMP_FAILURE" ||
              a?.details?.scenario === "pump_failure_risk"
          )
      : null;
  const fallbackTask =
    Array.isArray(waterData?.tasks)
      ? [...waterData.tasks]
          .reverse()
          .find((t: any) =>
            String(t?.title || "")
              .toLowerCase()
              .includes("pump")
          )
      : null;
  const primaryAssignment =
    Array.isArray(agentAnalysis?.routing_assignments) && agentAnalysis.routing_assignments.length > 0
      ? agentAnalysis.routing_assignments[0]
      : null;
  const assignedTechName =
    routedTechnician?.technician_name ||
    primaryAssignment?.technician_name ||
    latestPumpAlert?.details?.technician_name ||
    "Technician assigned";
  const assignedTaskType =
    routedTechnician?.task_type ||
    primaryAssignment?.task_type ||
    fallbackTask?.title ||
    "Inspect Pump";
  const displayTechName = assignedTechName;
  const hasTechnicianDispatch =
    Boolean(routedTechnician) ||
    Boolean(primaryAssignment) ||
    Boolean(latestPumpAlert?.details?.technician_name) ||
    Boolean(fallbackTask);
  const dispatchEtaMinutes =
    maintenanceRiskLevel === "CRITICAL"
      ? 15
      : maintenanceRiskLevel === "HIGH"
      ? 25
      : maintenanceRiskLevel === "MEDIUM"
      ? 35
      : 45;

  if (loading) {
    return (
      <LinearGradient colors={["#0ea5e9", "#e0f2fe"]} style={{ flex: 1 }}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color="white" />
          <Text style={styles.loadingText}>Loading detailed analysis...</Text>
        </View>
      </LinearGradient>
    );
  }

  return (
    <LinearGradient colors={["#0ea5e9", "#e0f2fe"]} style={{ flex: 1 }}>
      <ScrollView
        contentContainerStyle={styles.container}
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.pageTitle}>System Details</Text>

        {/* RISK LEVEL + AI ANALYSIS - COMBINED */}
        {waterData && (
          <View style={styles.statusCard}>
            <Text style={styles.sectionTitle}>🤖 SUMMARY</Text>
            <View style={styles.aiAnalysisContent}>
              {/* Water Level Status */}
              <View style={[styles.statusIndicator, {
                backgroundColor: waterData.tank_status?.level_percentage >= 70 ? "#f0fdf4" :
                                waterData.tank_status?.level_percentage >= 30 ? "#fffbeb" : "#fef2f2"
              }]}>
                <Text style={[styles.statusEmoji, {
                  color: waterData.tank_status?.level_percentage >= 70 ? "#22c55e" :
                         waterData.tank_status?.level_percentage >= 30 ? "#f59e0b" : "#ef4444"
                }]}>
                  {waterData.tank_status?.level_percentage >= 70 ? "✅" :
                   waterData.tank_status?.level_percentage >= 30 ? "⚠️" : "🚨"}
                </Text>
                <Text style={styles.statusText}>
                  {waterData.tank_status?.level_percentage >= 70 ? "Water level is healthy. No immediate action required." :
                   waterData.tank_status?.level_percentage >= 30 ? "Water level is low. Schedule refill soon." :
                   "Water level is CRITICAL. Emergency refill required!"}
                </Text>
              </View>

              {/* Reasoning */}
              <View style={styles.reasoningBox}>
                <Text style={styles.reasoningTitle}>Reasoning:</Text>
                <Text style={styles.reasoningText}>
                  {waterData.ai_reasoning || "AI reasoning not available."}
                </Text>
              </View>

              {/* Priority */}
              <View style={styles.priorityBox}>
                <Text style={styles.priorityLabel}>Priority:</Text>
                <Text style={[styles.priorityValue, {
                  color: waterData.tank_status?.level_percentage >= 70 ? "#22c55e" :
                         waterData.tank_status?.level_percentage >= 30 ? "#f59e0b" : "#ef4444"
                }]}>
                  {waterData.ai_priority || (waterData.tank_status?.level_percentage >= 70 ? "LOW" :
                   waterData.tank_status?.level_percentage >= 30 ? "HIGH" : "CRITICAL")}
                </Text>
              </View>

              {/* Recommended Action */}
              <View style={styles.actionBox}>
                <Text style={styles.actionTitle}>Recommended Action:</Text>
                <Text style={styles.actionValue}>
                  {waterData.ai_action || (waterData.tank_status?.level_percentage >= 70 ? "monitor" :
                   waterData.tank_status?.level_percentage >= 30 ? "schedule_refill" : "emergency_refill")}
                </Text>
              </View>
            </View>
          </View>
        )}

        {/* ⚠️ PREDICTIVE MAINTENANCE - ALWAYS SHOW */}
        {(agentAnalysis || maintenance) && (
          <View style={styles.maintenanceCard}>
            <View style={styles.cardHeader}>
              <Ionicons
                name="warning"
                size={24}
                color={
                  maintenanceRiskLevel === "CRITICAL"
                    ? "#ef4444"
                    : maintenanceRiskLevel === "HIGH"
                    ? "#f59e0b"
                    : "#22c55e"
                }
              />
              <Text style={styles.cardTitle}>⚠️ Predictive Maintenance</Text>
            </View>
            <View style={styles.divider} />
            
            {/* Risk Score Display */}
            <View style={styles.riskScoreContainer}>
              <View style={styles.riskCircle}>
                <Text style={styles.riskValue}>
                  {(maintenanceRiskScore * 100).toFixed(0)}%
                </Text>
              </View>
              <View style={styles.riskDetails}>
                <Text style={styles.riskLabel}>Risk Level:</Text>
                <Text
                  style={[
                    styles.riskLevelText,
                    { 
                      color: maintenanceRiskLevel === "CRITICAL" ? "#ef4444" :
                             maintenanceRiskLevel === "HIGH" ? "#f59e0b" :
                             maintenanceRiskLevel === "MEDIUM" ? "#eab308" : "#22c55e"
                    },
                  ]}
                >
                  {maintenanceRiskLevel}
                </Text>
              </View>
            </View>

            {/* Risk Breakdown */}
            <View style={styles.riskBreakdown}>
              <Text style={styles.breakdownTitle}>Risk Factors:</Text>
              <View style={styles.factorItem}>
                <Ionicons
                  name={maintenanceSignals.high_vibration ? "alert-circle" : "checkmark-circle"}
                  size={16}
                  color={maintenanceSignals.high_vibration ? "#ef4444" : "#22c55e"}
                />
                <Text style={styles.factorText}>
                  Vibration: {Number(maintenanceSignals.vibration || 0).toFixed(2)} mm/s
                  {maintenanceSignals.high_vibration ? " (High)" : " (Normal)"}
                </Text>
              </View>
              <View style={styles.factorItem}>
                <Ionicons
                  name={maintenanceSignals.high_temperature ? "alert-circle" : "checkmark-circle"}
                  size={16}
                  color={maintenanceSignals.high_temperature ? "#ef4444" : "#22c55e"}
                />
                <Text style={styles.factorText}>
                  Temperature: {Number(maintenanceSignals.temperature || 0).toFixed(1)}°C
                  {maintenanceSignals.high_temperature ? " (High)" : " (Normal)"}
                </Text>
              </View>
              <View style={styles.factorItem}>
                <Ionicons
                  name={maintenanceSignals.low_pressure ? "alert-circle" : "checkmark-circle"}
                  size={16}
                  color={maintenanceSignals.low_pressure ? "#ef4444" : "#22c55e"}
                />
                <Text style={styles.factorText}>
                  Pressure: {Number(maintenanceSignals.pressure || 0).toFixed(1)} psi
                  {maintenanceSignals.low_pressure ? " (Low)" : " (Stable)"}
                </Text>
              </View>
            </View>
          </View>
        )}

        {/* 🚚 TECHNICIAN DISPATCH */}
        {hasTechnicianDispatch && (
          <View style={styles.dispatchCard}>
            <View style={styles.cardHeader}>
              <Ionicons name="construct" size={24} color="#2563eb" />
              <Text style={styles.cardTitle}>🚚 Technician Dispatch</Text>
            </View>
            <View style={styles.divider} />
            <View style={styles.dispatchRow}>
              <Text style={styles.dispatchLabel}>Technician</Text>
              <Text style={styles.dispatchValue}>{displayTechName}</Text>
            </View>
            <View style={styles.dispatchRow}>
              <Text style={styles.dispatchLabel}>ETA</Text>
              <Text style={styles.dispatchValue}>{dispatchEtaMinutes} minutes</Text>
            </View>
            <View style={styles.dispatchRow}>
              <Text style={styles.dispatchLabel}>Assignment</Text>
              <Text style={styles.dispatchValue}>{assignedTaskType}</Text>
            </View>
            <Text style={styles.dispatchSubtext}>Live routing reference: {displayTechName}</Text>
          </View>
        )}

        {/* 🎯 ROUTING ASSIGNMENTS */}
        {agentAnalysis && agentAnalysis.routing_assignments && agentAnalysis.routing_assignments.length > 0 && (
          <View style={styles.routingCard}>
            <View style={styles.cardHeader}>
              <Ionicons name="people" size={24} color="#8b5cf6" />
              <Text style={styles.cardTitle}>🎯 Routing Assignments</Text>
            </View>
            <View style={styles.divider} />
            {agentAnalysis.routing_assignments.map((assignment: any, idx: number) => (
              <View key={idx} style={styles.assignmentItem}>
                <View style={styles.technicianInfo}>
                  <Ionicons name="person" size={20} color="#3b82f6" />
                  <View style={{ flex: 1, marginLeft: 12 }}>
                    <Text style={styles.technicianName}>{assignment.technician_name || "Technician"}</Text>
                    <Text style={styles.technicianTask}>{assignment.task_type || "Task Assignment"}</Text>
                  </View>
                </View>
                <View style={styles.skillsTags}>
                  {(assignment.matched_skills || []).slice(0, 2).map((skill: string, i: number) => (
                    <Text key={i} style={styles.skillTag}>{skill}</Text>
                  ))}
                </View>
              </View>
            ))}
          </View>
        )}

        {/* FORECAST */}
        {forecast && (
          <View style={styles.statusCard}>
            <Text style={styles.sectionTitle}>📈 24-Hour Forecast</Text>
            <View style={styles.forecastItem}>
              <Text style={styles.forecastLabel}>Demand Level:</Text>
              <Text style={[styles.forecastValue, {
                color: forecast.demand_level === "CRITICAL" ? "#ef4444" :
                       forecast.demand_level === "HIGH" ? "#f59e0b" :
                       forecast.demand_level === "MEDIUM" ? "#eab308" : "#22c55e"
              }]}>
                {forecast.demand_level}
              </Text>
            </View>
            <View style={styles.forecastItem}>
              <Text style={styles.forecastLabel}>Forecast Total:</Text>
              <Text style={styles.forecastValue}>{forecast.forecast_total?.toFixed(0) || "N/A"} L</Text>
            </View>
            <View style={styles.forecastItem}>
              <Text style={styles.forecastLabel}>Confidence:</Text>
              <Text style={styles.forecastValue}>{forecast.confidence_level || "High"}</Text>
            </View>
            <View style={[styles.forecastItem, { marginBottom: 0 }]}>
              <Text style={styles.forecastLabel}>Recommendation:</Text>
              <Text style={[styles.recommendationText, { flex: 1, marginLeft: 0 }]}>{forecast.recommendation}</Text>
            </View>
          </View>
        )}

        {/* Execution state is tracked in History tab; details focuses on diagnostics. */}

        <View style={{ height: 30 }} />
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 15,
    paddingTop: 20,
    paddingBottom: 30,
  },

  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },

  loadingText: {
    color: "white",
    fontSize: 16,
    marginTop: 12,
    fontWeight: "600",
  },

  pageTitle: {
    fontSize: 28,
    fontWeight: "bold",
    color: "white",
    marginBottom: 6,
    textAlign: "center",
  },

  pageSubtitle: {
    fontSize: 13,
    color: "rgba(255,255,255,0.8)",
    textAlign: "center",
    marginBottom: 20,
  },

  // NEW SIMPLE STYLES
  statusCard: {
    backgroundColor: "rgba(255, 255, 255, 0.95)",
    borderRadius: 12,
    padding: 16,
    marginBottom: 14,
  },

  sectionTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#111",
    marginBottom: 12,
  },

  levelBox: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },

  levelPercent: {
    fontSize: 36,
    fontWeight: "800",
  },

  levelState: {
    fontSize: 14,
    fontWeight: "600",
  },

  riskRow: {
    flexDirection: "row",
    justifyContent: "space-around",
  },

  riskBox: {
    alignItems: "center",
  },

  riskScore: {
    fontSize: 32,
    fontWeight: "800",
    color: "#111",
  },

  forecastItem: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: "#e5e7eb",
  },

  forecastLabel: {
    fontSize: 13,
    fontWeight: "600",
    color: "#666",
  },

  forecastValue: {
    fontSize: 14,
    fontWeight: "700",
    color: "#111",
  },

  assignmentRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: "#fecaca",
  },

  assignLabel: {
    fontSize: 13,
    fontWeight: "600",
    color: "#666",
  },

  assignValue: {
    fontSize: 13,
    fontWeight: "700",
    color: "#111",
  },

  supervisorCard: {
    backgroundColor: "rgba(255, 255, 255, 0.95)",
    borderRadius: 15,
    padding: 16,
    marginBottom: 16,
    borderLeftWidth: 4,
    borderLeftColor: "#3b82f6",
  },

  maintenanceCard: {
    backgroundColor: "rgba(255, 255, 255, 0.95)",
    borderRadius: 15,
    padding: 16,
    marginBottom: 16,
    borderLeftWidth: 4,
    borderLeftColor: "#f59e0b",
  },
  dispatchCard: {
    backgroundColor: "rgba(255, 255, 255, 0.95)",
    borderRadius: 15,
    padding: 16,
    marginBottom: 16,
    borderLeftWidth: 4,
    borderLeftColor: "#2563eb",
  },
  dispatchRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: "#e5e7eb",
  },
  dispatchLabel: {
    fontSize: 13,
    color: "#6b7280",
    fontWeight: "600",
  },
  dispatchValue: {
    fontSize: 14,
    color: "#111827",
    fontWeight: "700",
  },
  dispatchSubtext: {
    marginTop: 10,
    fontSize: 12,
    color: "#64748b",
    fontStyle: "italic",
  },

  routingCard: {
    backgroundColor: "rgba(255, 255, 255, 0.95)",
    borderRadius: 15,
    padding: 16,
    marginBottom: 16,
    borderLeftWidth: 4,
    borderLeftColor: "#8b5cf6",
  },

  mlCard: {
    backgroundColor: "rgba(255, 255, 255, 0.95)",
    borderRadius: 15,
    padding: 16,
    marginBottom: 16,
    borderLeftWidth: 4,
    borderLeftColor: "#06b6d4",
  },

  summaryCard: {
    backgroundColor: "rgba(255, 255, 255, 0.95)",
    borderRadius: 15,
    padding: 16,
    marginBottom: 16,
    borderLeftWidth: 4,
    borderLeftColor: "#06b6d4",
  },

  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 10,
  },

  cardTitle: {
    fontSize: 16,
    fontWeight: "bold",
    color: "#111",
    marginLeft: 10,
  },

  divider: {
    height: 1,
    backgroundColor: "#e0e0e0",
    marginBottom: 12,
  },

  analysisText: {
    fontSize: 14,
    color: "#333",
    lineHeight: 20,
    marginBottom: 12,
  },

  analysisHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },

  analysisTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#111",
  },

  riskBadge: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
    justifyContent: "center",
    alignItems: "center",
  },

  riskBadgeText: {
    fontSize: 12,
    fontWeight: "700",
    color: "white",
  },

  aiAnalysisContent: {
    marginTop: 8,
  },

  statusIndicator: {
    flexDirection: "row",
    alignItems: "center",
    padding: 12,
    borderRadius: 8,
    marginBottom: 12,
  },

  statusEmoji: {
    fontSize: 24,
    marginRight: 12,
  },

  reasoningBox: {
    backgroundColor: "#fafafa",
    padding: 12,
    borderRadius: 8,
    marginBottom: 12,
  },

  reasoningTitle: {
    fontSize: 12,
    fontWeight: "700",
    color: "#111",
    marginBottom: 6,
  },

  reasoningText: {
    fontSize: 13,
    color: "#555",
    lineHeight: 18,
  },

  priorityBox: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 12,
    backgroundColor: "#f5f3ff",
    borderRadius: 8,
    marginBottom: 12,
  },

  priorityLabel: {
    fontSize: 12,
    fontWeight: "700",
    color: "#333",
  },

  priorityValue: {
    fontSize: 14,
    fontWeight: "700",
  },

  actionBox: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 12,
    backgroundColor: "#f9fafb",
    borderRadius: 8,
    borderLeftWidth: 3,
    borderLeftColor: "#0284c7",
  },

  actionTitle: {
    fontSize: 12,
    fontWeight: "700",
    color: "#333",
  },

  actionValue: {
    fontSize: 13,
    fontWeight: "600",
    color: "#0284c7",
  },

  statusBadge: {
    backgroundColor: "#f0fdf4",
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderLeftWidth: 3,
    borderLeftColor: "#22c55e",
  },

  statusText: {
    fontSize: 12,
    color: "#166534",
    fontWeight: "600",
  },

  riskScoreContainer: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 16,
    backgroundColor: "#f5f3ff",
    paddingVertical: 12,
    paddingHorizontal: 12,
    borderRadius: 10,
  },

  riskCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: "#f5f3ff",
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 2,
    borderColor: "#f59e0b",
  },

  riskValue: {
    fontSize: 24,
    fontWeight: "bold",
    color: "#f59e0b",
  },

  riskDetails: {
    marginLeft: 16,
    flex: 1,
  },

  riskLabel: {
    fontSize: 12,
    color: "#666",
    marginBottom: 4,
  },

  riskLevelText: {
    fontSize: 18,
    fontWeight: "bold",
  },

  riskBreakdown: {
    backgroundColor: "#fafafa",
    padding: 12,
    borderRadius: 10,
    marginTop: 12,
  },

  breakdownTitle: {
    fontSize: 13,
    fontWeight: "bold",
    color: "#333",
    marginBottom: 8,
  },

  factorItem: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
  },

  factorText: {
    fontSize: 12,
    color: "#555",
    marginLeft: 8,
  },

  assignmentItem: {
    backgroundColor: "#f0f9ff",
    padding: 12,
    borderRadius: 10,
    marginBottom: 10,
    borderLeftWidth: 3,
    borderLeftColor: "#3b82f6",
  },

  technicianInfo: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
  },

  technicianName: {
    fontSize: 14,
    fontWeight: "bold",
    color: "#111",
  },

  technicianTask: {
    fontSize: 12,
    color: "#666",
    marginTop: 2,
  },

  skillsTags: {
    flexDirection: "row",
    flexWrap: "wrap",
  },

  skillTag: {
    backgroundColor: "#dbeafe",
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 6,
    marginRight: 6,
    marginBottom: 4,
    fontSize: 11,
    color: "#0284c7",
    fontWeight: "600",
  },

  mlSection: {
    marginBottom: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#e0e0e0",
  },

  mlSectionTitle: {
    fontSize: 14,
    fontWeight: "bold",
    color: "#06b6d4",
    marginBottom: 10,
  },

  mlItem: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: "#f0f0f0",
  },

  mlItemLabel: {
    fontSize: 12,
    color: "#666",
    fontWeight: "600",
  },

  mlItemValue: {
    fontSize: 12,
    fontWeight: "bold",
    color: "#06b6d4",
  },

  peakHourBox: {
    backgroundColor: "#f0fdf4",
    padding: 12,
    borderRadius: 8,
    marginTop: 8,
  },

  recommendationBox: {
    flexDirection: "row",
    backgroundColor: "#fffbeb",
    borderLeftWidth: 4,
    borderLeftColor: "#f59e0b",
    padding: 12,
    borderRadius: 8,
    marginTop: 12,
  },

  recommendationText: {
    fontSize: 12,
    color: "#333",
    marginLeft: 10,
    flex: 1,
    fontStyle: "italic",
  },

  summaryItem: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: "#e0e0e0",
  },

  summaryLabel: {
    fontSize: 13,
    color: "#666",
    fontWeight: "600",
  },

  summaryValue: {
    fontSize: 14,
    fontWeight: "bold",
    color: "#06b6d4",
  },

  infoBox: {
    backgroundColor: "rgba(255, 255, 255, 0.95)",
    borderRadius: 12,
    padding: 16,
  },

  infoTitle: {
    fontSize: 14,
    fontWeight: "bold",
    color: "#111",
    marginBottom: 10,
  },

  infoText: {
    fontSize: 12,
    color: "#555",
    lineHeight: 18,
    marginBottom: 6,
  },

  criticalCard: {
    backgroundColor: "#fef2f2",
    borderRadius: 15,
    padding: 16,
    marginBottom: 16,
    borderLeftWidth: 5,
    borderLeftColor: "#ef4444",
  },

  criticalAssignment: {
    flexDirection: "row",
    backgroundColor: "white",
    borderRadius: 12,
    padding: 14,
    marginBottom: 12,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#fee2e2",
  },

  assignmentIcon: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: "#ef4444",
    justifyContent: "center",
    alignItems: "center",
    marginRight: 12,
  },

  assignmentTitle: {
    fontSize: 14,
    fontWeight: "bold",
    color: "#111",
    marginBottom: 3,
  },

  assignmentName: {
    fontSize: 13,
    fontWeight: "600",
    color: "#ef4444",
    marginBottom: 2,
  },

  assignmentDetail: {
    fontSize: 12,
    color: "#666",
    marginBottom: 2,
  },

  assignmentTime: {
    fontSize: 11,
    color: "#999",
    fontStyle: "italic",
  },

  assignmentStatus: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
    backgroundColor: "#fecaca",
    justifyContent: "center",
    alignItems: "center",
  },

  statusBadgeRed: {
    fontSize: 11,
    fontWeight: "bold",
    color: "#dc2626",
  },

  statusBadgeOrange: {
    fontSize: 11,
    fontWeight: "bold",
    color: "#d97706",
  },
});