import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  FlatList,
  Dimensions,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { useMode } from "../context/ModeContext";
import { API_BASE_URL } from "../../services/api";

export default function History() {
  const { tankViewMode, pumpViewMode } = useMode();
  const [tasks, setTasks] = useState<any[]>([]);
  const [createdTasks, setCreatedTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      console.log("📋 History: Loading task history from BLD_001...");
      
      // Fetch ALL tasks for this building to show complete history
      const taskRes = await fetch(`${API_BASE_URL}/tasks?building_id=BLD_001&limit=100`);
      const taskData = await taskRes.json();
      console.log("📋 Tasks loaded:", taskData?.length || 0, "tasks");
      setTasks(Array.isArray(taskData) ? taskData : []);

      // Fetch water data to get tasks created in worst case
      const waterRes = await fetch(
        `${API_BASE_URL}/water/run?building_id=BLD_001&mode=latest&tank_mode=${tankViewMode}&pump_mode=${pumpViewMode}`,
        { method: "POST" }
      );
      const waterData = await waterRes.json();
      
      // Add worst case created tasks to the list
      if (waterData?.created_tasks && waterData.created_tasks.length > 0) {
        console.log("📋 Worst case created tasks:", waterData.created_tasks);
        setCreatedTasks(waterData.created_tasks);
      }

      console.log("✅ History loaded successfully");
    } catch (e) {
      console.error("❌ Failed to load history data:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [tankViewMode, pumpViewMode]);

  const formatTaskTime = (createdAt: string | null) => {
    if (!createdAt) return "Just now";
    try {
      // Parse ISO format or standard date string
      const date = new Date(createdAt);
      
      // Check if date is valid
      if (isNaN(date.getTime())) {
        return "Just now";
      }
      
      // Convert to local time
      const hours = String(date.getHours()).padStart(2, "0");
      const minutes = String(date.getMinutes()).padStart(2, "0");
      return `${hours}:${minutes}`;
    } catch (e) {
      console.error("Error formatting time:", e);
      return "Just now";
    }
  };

  const renderTaskItem = ({ item }: { item: any }) => {
    const isCritical = item.priority === "CRITICAL";
    const isHigh = item.priority === "HIGH";

    // Use the task's actual created_at time
    const taskTime = formatTaskTime(item.created_at);
    
    // Status emoji
    const statusEmoji = item.status === "OPEN" ? "🔴" : "✅";

    return (
      <View style={[styles.taskCard, getPriorityColor(item.priority)]}>
        {/* Header: Time + Title + Priority */}
        <View style={styles.taskHeader}>
          <View style={{ flex: 1 }}>
            <Text style={styles.taskTime}>⏰ Created: {taskTime}</Text>
            <Text style={styles.taskTitle}>{item.title}</Text>
          </View>
          <View
            style={[
              styles.priorityBadge,
              item.priority === "CRITICAL" && { backgroundColor: "#ef4444" },
              item.priority === "HIGH" && { backgroundColor: "#f59e0b" },
              item.priority === "MEDIUM" && { backgroundColor: "#eab308" },
              item.priority === "LOW" && { backgroundColor: "#22c55e" },
            ]}
          >
            <Text style={styles.priorityText}>{item.priority[0]}</Text>
          </View>
        </View>

        {/* Description */}
        <Text style={styles.taskDesc}>{item.description}</Text>

        {/* Assignment/dispatch status - data-driven from task status */}
        {(isCritical || isHigh) && (
          <View style={styles.assignmentSection}>
            <Text style={styles.sectionTitle}>📋 Assignment Details</Text>
            <View style={styles.assignmentRow}>
              <Text style={styles.assignmentLabel}>📍 Status</Text>
              <Text style={[styles.assignmentValue, { color: "#ef4444", fontWeight: "700" }]}>
                {item.status === "OPEN" ? "🚀 IN DISPATCH" : "✅ COMPLETED"}
              </Text>
            </View>
          </View>
        )}

        {/* Footer: Asset + SLA + Status */}
        <View style={styles.taskFooterContainer}>
          <View style={styles.footerItemBox}>
            <Text style={styles.footerLabel}>Asset</Text>
            <Text style={styles.footerValue}>{item.asset_id}</Text>
          </View>
          <View style={styles.footerItemBox}>
            <Text style={styles.footerLabel}>SLA</Text>
            <Text style={styles.footerValue}>{item.sla_hours}h</Text>
          </View>
          <View style={styles.footerItemBox}>
            <Text style={styles.footerLabel}>Status</Text>
            <Text style={[styles.footerValue, item.status === "OPEN" ? { color: "#ef4444" } : { color: "#22c55e" }]}>
              {statusEmoji} {item.status}
            </Text>
          </View>
        </View>
      </View>
    );
  };

  const getPriorityColor = (priority: string) => {
    if (priority === "CRITICAL") return { borderLeftColor: "#ef4444" };
    if (priority === "HIGH") return { borderLeftColor: "#f59e0b" };
    if (priority === "MEDIUM") return { borderLeftColor: "#eab308" };
    return { borderLeftColor: "#22c55e" };
  };

  const allTasks = [...tasks, ...createdTasks]; // Combine both lists

  if (loading) {
    return (
      <LinearGradient colors={["#0ea5e9", "#e0f2fe"]} style={{ flex: 1 }}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color="white" />
          <Text style={styles.loadingText}>Loading dashboard...</Text>
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
        <Text style={styles.pageTitle}>📋 Task History</Text>
        <Text style={styles.pageSubtitle}>Complete log of all tasks and maintenance activities</Text>

        {/* TASKS LIST */}
        <View style={styles.tasksSection}>
          {allTasks.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyText}>✅ All tasks completed!</Text>
              <Text style={styles.emptySubtext}>No tasks in the system</Text>
            </View>
          ) : (
            <FlatList
              scrollEnabled={false}
              data={allTasks}
              keyExtractor={(item, index) => item.task_id?.toString() || index.toString()}
              renderItem={renderTaskItem}
            />
          )}
        </View>

        <View style={{ height: 20 }} />
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
    marginBottom: 8,
    textAlign: "center",
  },

  pageSubtitle: {
    fontSize: 13,
    color: "rgba(255, 255, 255, 0.8)",
    textAlign: "center",
    marginBottom: 16,
  },

  sectionTitle: {
    fontSize: 15,
    fontWeight: "bold",
    color: "white",
    marginBottom: 12,
  },

  stateCard: {
    backgroundColor: "rgba(255, 255, 255, 0.95)",
    borderRadius: 15,
    padding: 16,
    marginBottom: 16,
  },

  stateRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: "#e0e0e0",
  },

  stateLabel: {
    fontSize: 14,
    color: "#666",
    fontWeight: "600",
  },

  stateValue: {
    fontSize: 16,
    fontWeight: "bold",
    color: "#0284c7",
  },

  statsCard: {
    backgroundColor: "rgba(255, 255, 255, 0.95)",
    borderRadius: 15,
    padding: 16,
    marginBottom: 16,
  },

  statsRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 12,
  },

  statItem: {
    backgroundColor: "#f0f9ff",
    borderRadius: 10,
    padding: 12,
    alignItems: "center",
    flex: 1,
    marginHorizontal: 4,
  },

  statCount: {
    fontSize: 22,
    fontWeight: "bold",
    color: "#0284c7",
  },

  statLabel: {
    fontSize: 11,
    color: "#666",
    marginTop: 4,
  },

  forecastCard: {
    backgroundColor: "rgba(255, 255, 255, 0.95)",
    borderRadius: 15,
    padding: 16,
    marginBottom: 16,
  },

  forecastContent: {
    marginBottom: 12,
  },

  forecastItem: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: "#e0e0e0",
  },

  forecastLabel: {
    fontSize: 13,
    color: "#666",
    fontWeight: "600",
  },

  forecastValue: {
    fontSize: 14,
    fontWeight: "bold",
    color: "#0284c7",
  },

  recommendationBox: {
    backgroundColor: "#fffbeb",
    borderLeftWidth: 4,
    borderLeftColor: "#f59e0b",
    padding: 12,
    borderRadius: 8,
  },

  recommendationText: {
    fontSize: 13,
    color: "#333",
    fontStyle: "italic",
  },

  tasksSection: {
    marginBottom: 16,
  },

  emptyState: {
    backgroundColor: "rgba(255, 255, 255, 0.95)",
    borderRadius: 12,
    padding: 30,
    alignItems: "center",
  },

  emptyText: {
    fontSize: 18,
    fontWeight: "bold",
    color: "#22c55e",
  },

  emptySubtext: {
    fontSize: 13,
    color: "#888",
    marginTop: 6,
  },

  taskCard: {
    backgroundColor: "white",
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    borderLeftWidth: 5,
  },

  taskHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 8,
  },

  taskTitle: {
    fontSize: 14,
    fontWeight: "bold",
    color: "#111",
  },

  taskTime: {
    fontSize: 11,
    color: "#0284c7",
    fontWeight: "600",
    marginBottom: 4,
  },

  taskDesc: {
    fontSize: 12,
    color: "#888",
    marginTop: 4,
  },

  priorityBadge: {
    width: 28,
    height: 28,
    borderRadius: 14,
    justifyContent: "center",
    alignItems: "center",
    marginLeft: 8,
  },

  priorityText: {
    fontSize: 13,
    fontWeight: "bold",
    color: "white",
  },

  taskFooter: {
    flexDirection: "row",
    justifyContent: "space-between",
    flexWrap: "wrap",
  },

  taskFooterContainer: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 10,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: "#e0e0e0",
  },

  footerItemBox: {
    flex: 1,
    alignItems: "center",
    paddingHorizontal: 6,
  },

  footerLabel: {
    fontSize: 11,
    color: "#999",
    fontWeight: "600",
    marginBottom: 4,
  },

  footerValue: {
    fontSize: 12,
    fontWeight: "700",
    color: "#0284c7",
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
    marginBottom: 8,
    lineHeight: 18,
  },

  // Peak Hour Box Styles
  peakHourBox: {
    backgroundColor: "#f0fdf4",
    borderLeftWidth: 4,
    borderLeftColor: "#22c55e",
    padding: 12,
    borderRadius: 8,
    marginTop: 10,
  },

  peakLabel: {
    fontSize: 13,
    fontWeight: "bold",
    color: "#166534",
    marginBottom: 6,
  },

  peakText: {
    fontSize: 12,
    color: "#333",
    marginVertical: 3,
  },

  // ML Card Styles
  mlCard: {
    backgroundColor: "rgba(255, 255, 255, 0.95)",
    borderRadius: 15,
    padding: 16,
    marginBottom: 16,
    borderWidth: 2,
    borderColor: "#a78bfa",
  },

  mlMetricItem: {
    marginBottom: 14,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#e0e0e0",
  },

  // Assignment Section Styles
  assignmentSection: {
    backgroundColor: "#fef2f2",
    borderLeftWidth: 4,
    borderLeftColor: "#ef4444",
    padding: 12,
    borderRadius: 8,
    marginTop: 10,
    marginBottom: 10,
  },

  assignmentRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },

  assignmentLabel: {
    fontSize: 12,
    fontWeight: "600",
    color: "#666",
    flex: 1,
  },

  assignmentValue: {
    fontSize: 12,
    fontWeight: "700",
    color: "#111",
    textAlign: "right",
  },
});
