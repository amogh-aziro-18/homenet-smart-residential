import { Platform } from "react-native";
import * as Notifications from "expo-notifications";

const ANDROID_DEFAULT_CHANNEL_ID = "homenet-default";

// Configure how notifications appear
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

async function ensureAndroidChannel() {
  if (Platform.OS !== "android") return;
  await Notifications.setNotificationChannelAsync(ANDROID_DEFAULT_CHANNEL_ID, {
    name: "HOMENET alerts",
    importance: Notifications.AndroidImportance.MAX,
    vibrationPattern: [0, 250, 250, 250],
    sound: "default",
  });
}

/**
 * Send a local push notification (immediate)
 */
export async function sendNotification(
  title: string,
  body: string,
  data?: Record<string, string>
) {
  try {
    await ensureAndroidChannel();
    let { status } = await Notifications.getPermissionsAsync();
    if (status !== "granted") {
      const req = await Notifications.requestPermissionsAsync();
      status = req.status;
    }
    if (status !== "granted") {
      console.warn("Notifications not granted after request; skipping local alert");
      return;
    }

    await Notifications.scheduleNotificationAsync({
      content: {
        title,
        body,
        data: data || {},
        sound: "default",
        ...(Platform.OS === "android" && {
          channelId: ANDROID_DEFAULT_CHANNEL_ID,
        }),
      },
      trigger: null,
    });
  } catch (error) {
    console.error("Failed to send notification:", error);
  }
}

/**
 * Request notification permissions (required on iOS/Android)
 */
export async function requestNotificationPermissions() {
  try {
    await ensureAndroidChannel();
    const { status } = await Notifications.requestPermissionsAsync();
    return status === "granted";
  } catch (error) {
    console.error("Failed to request notification permissions:", error);
    return false;
  }
}

/**
 * Send critical water tank alert
 */
export async function sendCriticalWaterAlert(tankId: string, level: number) {
  await sendNotification(
    "🚨 CRITICAL ALERT",
    `Tank ${tankId} is critically low at ${level.toFixed(1)}%. Immediate refill needed!`,
    {
      type: "critical_water_alert",
      tank_id: tankId,
      level: level.toString(),
    }
  );
}

/**
 * Send low water alert
 */
export async function sendLowWaterAlert(tankId: string, level: number) {
  await sendNotification(
    "⚠️ LOW WATER LEVEL",
    `Tank ${tankId} is low at ${level.toFixed(1)}%. Schedule refill soon.`,
    {
      type: "low_water_alert",
      tank_id: tankId,
      level: level.toString(),
    }
  );
}

/**
 * Send predictive pump-failure alert with technician assignment.
 */
export async function sendPumpFailureRepairAlert(
  pumpId: string,
  technicianName: string,
  includeRefill: boolean = true
) {
  const refillText = includeRefill
    ? "Please store/fill water now as the pump is under repair."
    : "Pump is under repair. Please store water as a precaution.";

  await sendNotification(
    "🛠️ PUMP FAILURE RISK",
    `Pump ${pumpId} is under failure-risk repair. ${technicianName} has been assigned. ${refillText}`,
    {
      type: "pump_failure_alert",
      pump_id: pumpId,
      technician_name: technicianName,
      refill_advice: includeRefill ? "yes" : "no",
    }
  );
}

/**
 * Combined alert when both tank and pump worst-case scenarios are active.
 */
export async function sendCombinedWorstCaseAlert(
  tankId: string,
  pumpId: string,
  technicianName: string
) {
  await sendNotification(
    "🚨 COMBINED EMERGENCY ALERT",
    `Tank ${tankId} is low and pump ${pumpId} is under repair. ${technicianName} has been assigned. Please store/fill water immediately.`,
    {
      type: "combined_worst_case_alert",
      tank_id: tankId,
      pump_id: pumpId,
      technician_name: technicianName,
    }
  );
}
