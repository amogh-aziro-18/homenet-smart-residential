import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  TouchableOpacity,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { useMode } from "../context/ModeContext";
import { API_BASE_URL } from "../../services/api";

export default function Notifications() {
  const { tankViewMode, pumpViewMode } = useMode();
  const [alerts, setAlerts] = useState<any[]>([]);
  const [filter, setFilter] = useState<"BOTH" | "TANK" | "PUMP">("BOTH");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      await fetch(
        `${API_BASE_URL}/water/run?building_id=BLD_001&mode=latest&tank_mode=${tankViewMode}&pump_mode=${pumpViewMode}`,
        {
          method: "POST",
        }
      );

      // Pull normalized notifications from backend.
      const res = await fetch(`${API_BASE_URL}/notifications?building_id=BLD_001&limit=100`);
      const notifData = await res.json();

      const allAlerts = Array.isArray(notifData)
        ? notifData
        : notifData
        ? [notifData]
        : [];

      console.log("📢 Alerts loaded:", allAlerts.length, "alert(s)");
      setAlerts(allAlerts);
    } catch (e) {
      console.error("❌ Failed to load alerts:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [tankViewMode, pumpViewMode]);

  const getSeverityColor = (severity: string) => {
    if (severity === "CRITICAL") return "#ef4444";
    if (severity === "HIGH") return "#f59e0b";
    if (severity === "MEDIUM") return "#eab308";
    return "#22c55e";
  };

  const getSeverityIcon = (severity: string) => {
    if (severity === "CRITICAL") return "alert-circle";
    if (severity === "HIGH") return "warning";
    if (severity === "MEDIUM") return "information";
    return "checkmark-circle";
  };

  const renderAlertItem = (item: any, idx: number) => (
    <View
      key={idx}
      style={[
        styles.alertCard,
        { borderLeftColor: getSeverityColor(item.severity) },
      ]}
    >
      <View style={styles.alertHeader}>
        <View style={styles.alertTitleRow}>
          <Ionicons
            name={getSeverityIcon(item.severity)}
            size={22}
            color={getSeverityColor(item.severity)}
            style={{ marginRight: 10 }}
          />
          <Text
            style={[
              styles.alertTitle,
              { color: getSeverityColor(item.severity) },
            ]}
          >
            {item.asset || item.category || item.severity}
          </Text>
        </View>
        <Text style={styles.alertTime}>
          {new Date(item.created_at || Date.now()).toLocaleTimeString()}
        </Text>
      </View>
      <Text style={styles.alertMessage}>{item.title}</Text>
      <Text style={styles.alertDescription}>{item.message}</Text>
      {!!item.action && <Text style={styles.actionText}>Action: {item.action}</Text>}
      {!!item.category && (
        <Text style={styles.categoryText}>Category: {item.category}</Text>
      )}
      {item.related_task_id && (
        <View style={styles.taskLink}>
          <Ionicons name="link" size={14} color="#0284c7" />
          <Text style={styles.taskLinkText}>Task: {item.related_task_id}</Text>
        </View>
      )}
    </View>
  );

  if (loading) {
    return (
      <LinearGradient colors={["#0ea5e9", "#e0f2fe"]} style={{ flex: 1 }}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color="white" />
          <Text style={styles.loadingText}>Loading alerts...</Text>
        </View>
      </LinearGradient>
    );
  }

  const filteredAlerts = alerts.filter((a) => {
    if (filter === "BOTH") return true;
    if (filter === "TANK") return a.category === "WATER_LEVEL" || a.asset === "TANK";
    return a.category === "PUMP_FAILURE" || a.asset === "PUMP";
  });

  return (
    <LinearGradient colors={["#0ea5e9", "#e0f2fe"]} style={{ flex: 1 }}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>🔔 Alert History</Text>
        <View style={styles.filterRow}>
          {(["BOTH", "TANK", "PUMP"] as const).map((key) => (
            <TouchableOpacity
              key={key}
              style={[styles.filterChip, filter === key && styles.filterChipActive]}
              onPress={() => setFilter(key)}
            >
              <Text style={[styles.filterChipText, filter === key && styles.filterChipTextActive]}>
                {key}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {filteredAlerts.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="checkmark-done-circle" size={60} color="#22c55e" />
            <Text style={styles.emptyTitle}>All Clear!</Text>
            <Text style={styles.emptyText}>No alerts at this time</Text>
          </View>
        ) : (
          <View style={styles.alertsList}>
            {filteredAlerts.map((alert, idx) => renderAlertItem(alert, idx))}
          </View>
        )}

        {filteredAlerts.length > 0 && (
          <TouchableOpacity style={styles.clearButton} onPress={() => setAlerts([])}>
            <Text style={styles.clearButtonText}>Clear All Alerts</Text>
          </TouchableOpacity>
        )}
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
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

  title: {
    fontSize: 28,
    fontWeight: "bold",
    color: "white",
    marginBottom: 20,
    textAlign: "center",
  },

  filterRow: {
    flexDirection: "row",
    justifyContent: "center",
    gap: 10,
    marginBottom: 14,
  },

  filterChip: {
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 14,
    backgroundColor: "rgba(255,255,255,0.35)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.55)",
  },

  filterChipActive: {
    backgroundColor: "white",
    borderColor: "white",
  },

  filterChipText: {
    color: "white",
    fontWeight: "700",
    fontSize: 12,
  },

  filterChipTextActive: {
    color: "#0369a1",
  },

  alertsList: {
    marginBottom: 20,
  },

  alertCard: {
    backgroundColor: "white",
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderLeftWidth: 5,
  },

  alertHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 10,
  },

  alertTitleRow: {
    flexDirection: "row",
    alignItems: "center",
    flex: 1,
  },

  alertTitle: {
    fontSize: 16,
    fontWeight: "bold",
  },

  alertTime: {
    fontSize: 12,
    color: "#999",
  },

  alertMessage: {
    fontSize: 15,
    fontWeight: "600",
    color: "#333",
    marginBottom: 6,
  },

  alertDescription: {
    fontSize: 13,
    color: "#666",
    lineHeight: 18,
    marginBottom: 8,
  },

  categoryText: {
    fontSize: 11,
    color: "#64748b",
    marginTop: 2,
    marginBottom: 4,
    fontWeight: "600",
  },

  actionText: {
    fontSize: 12,
    color: "#0f766e",
    marginTop: 2,
    marginBottom: 2,
    fontWeight: "700",
  },

  taskLink: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#dbeafe",
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 6,
    marginTop: 8,
  },

  taskLinkText: {
    fontSize: 12,
    color: "#0284c7",
    fontWeight: "600",
    marginLeft: 6,
  },

  emptyState: {
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 60,
  },

  emptyTitle: {
    fontSize: 24,
    fontWeight: "bold",
    color: "#22c55e",
    marginTop: 16,
  },

  emptyText: {
    fontSize: 14,
    color: "#666",
    marginTop: 8,
  },

  clearButton: {
    backgroundColor: "#ef4444",
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: "center",
  },

  clearButtonText: {
    color: "white",
    fontSize: 16,
    fontWeight: "bold",
  },
});
