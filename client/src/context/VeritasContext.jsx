
import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState
} from "react";

const VeritasContext = createContext(null);

export function VeritasProvider({ children }) {

  // ==========================================
  // SHARED STATE
  // ==========================================

  const [leanbots, setLeanbots] = useState({});
  const [trafficState, setTrafficState] = useState(null);
  const [connected, setConnected] = useState(false);

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

    const ws = new WebSocket("ws://127.0.0.1:8000/ws");

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

            setLeanbots(message.leanbots);
            setTrafficState(message.traffic_state);

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

  // ==========================================
  // CONTEXT PROVIDER
  // ==========================================

  return (
    <VeritasContext.Provider
      value={{
        leanbots,
        trafficState,
        connected,
        frames
      }}
    >
      {children}
    </VeritasContext.Provider>
  );
}

// ==========================================
// CUSTOM HOOK
// ==========================================

export function useVeritas() {

  const context = useContext(VeritasContext);

  if (!context) {
    throw new Error(
      "useVeritas must be used within VeritasProvider"
    );
  }

  return context;
}
