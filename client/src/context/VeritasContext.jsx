
import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState
} from "react";
import { defaultTrafficCheckers } from "../data/trafficCheckers";

const VeritasContext = createContext(null);
const apiOrigin = `${window.location.protocol === "https:" ? "https:" : "http:"}//${window.location.hostname || "127.0.0.1"}:8000`;

export function VeritasProvider({ children }) {

  // ==========================================
  // SHARED STATE
  // ==========================================

  const [leanbots, setLeanbots] = useState([]);
  const [trafficStates, setTrafficStates] = useState(() =>
    Object.fromEntries(defaultTrafficCheckers.map(checker => [checker.id, "RED"]))
  );
  const [trafficCheckers, setTrafficCheckers] = useState(defaultTrafficCheckers);
  const [intersectionZone, setIntersectionZone] = useState("main_intersection");
  const [connected, setConnected] = useState(false);
  const [footSnapshot, setFootSnapshot] = useState(null);

  const [frames, setFrames] = useState({
    TOPDOWN: null,
    FOOT: null
  });

  // ==========================================
  // REFS
  // ==========================================

  const pendingCamera = useRef(null);
  const frameUrls = useRef({});

  // ==========================================
  // WEBSOCKET CONNECTION
  // ==========================================

  useEffect(() => {

    console.log("[VERITAS] Initializing WebSocket...");

    const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
    const wsHost = window.location.hostname || "127.0.0.1";
    const ws = new WebSocket(`${wsProtocol}://${wsHost}:8000/ws`);

    ws.binaryType = "blob";

    ws.onopen = () => {
      console.log("[WS] Connected successfully");
      setConnected(true);
    };

    ws.onmessage = (event) => {

      // ==================================
      // JSON MESSAGES
      // ==================================

      if (typeof event.data === "string") {

        try {

          const message = JSON.parse(event.data);

          if (message.type === "state_snapshot") {

            setLeanbots(Array.isArray(message.leanbots) ? message.leanbots : []);
            setTrafficStates(message.traffic_states ?? {});
            if (message.traffic_checkers?.length) {
              setTrafficCheckers(message.traffic_checkers);
            }
            if (message.intersection_zone) {
              setIntersectionZone(message.intersection_zone);
            }

          }

          else if (message.type === "foot_snapshot") {
            setFootSnapshot(message);
          }

          else if (message.type === "traffic_state") {
            setTrafficStates(message.traffic_states ?? {});
            if (message.traffic_checkers?.length) {
              setTrafficCheckers(message.traffic_checkers);
            }
            if (message.intersection_zone) {
              setIntersectionZone(message.intersection_zone);
            }
          }

          else if (message.type === "frame") {
            console.log()
            pendingCamera.current = message.camera_id;

          }

        } catch (error) {

          console.error("[WS] JSON parsing error:", error);

        }

        return;
      }

      // ==================================
      // BINARY JPEG FRAMES
      // ==================================

      if (event.data instanceof Blob) {

        const cameraId = pendingCamera.current;

        if (!cameraId) {
          console.warn("[WS] Frame received without camera metadata");
          return;
        }

        if (!["TOPDOWN", "FOOT"].includes(cameraId)) {
          console.warn("[WS] Unknown camera:", cameraId);
          pendingCamera.current = null;
          return;
        }

        const jpegBlob = event.data.slice(
          0,
          event.data.size,
          "image/jpeg"
        );

        const newUrl = URL.createObjectURL(jpegBlob);

        // Release previous frame URL
        if (frameUrls.current[cameraId]) {
          URL.revokeObjectURL(frameUrls.current[cameraId]);
        }

        frameUrls.current[cameraId] = newUrl;

        setFrames(previous => ({
          ...previous,
          [cameraId]: newUrl
        }));

        pendingCamera.current = null;
      }
    };

    ws.onerror = (error) => {
      console.error("[WS] Connection error:", error);
    };

    ws.onclose = (event) => {

      console.log("[WS] Closed:", {
        code: event.code,
        reason: event.reason,
        clean: event.wasClean
      });

      setConnected(false);
    };

    // ==================================
    // CLEANUP
    // ==================================

    return () => {

      console.log("[VERITAS] Cleaning up WebSocket");

      ws.close();

      Object.values(frameUrls.current).forEach(url => {
        URL.revokeObjectURL(url);
      });

      frameUrls.current = {};
      pendingCamera.current = null;

    };

  }, []);

  const setTrafficState = async (checkerId, state) => {
    const response = await fetch(`${apiOrigin}/api/traffic-state`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ checker_id: checkerId, state }),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || "Could not update traffic state");
    }
    setTrafficStates(previous => ({
      ...previous,
      [checkerId]: result.traffic_state,
    }));
    return result.traffic_state;
  };

  // ==========================================
  // CONTEXT PROVIDER
  // ==========================================

  return (
    <VeritasContext.Provider
      value={{
        leanbots,
        trafficStates,
        trafficCheckers,
        intersectionZone,
        connected,
        frames,
        footSnapshot,
        setTrafficState
      }}
    >
      {children}
    </VeritasContext.Provider>
  );
}

// ==========================================
// CUSTOM HOOK
// ==========================================

// The context module intentionally exports both its provider and consumer hook.
// eslint-disable-next-line react-refresh/only-export-components
export function useVeritas() {

  const context = useContext(VeritasContext);

  if (!context) {
    throw new Error(
      "useVeritas must be used within VeritasProvider"
    );
  }

  return context;
}
