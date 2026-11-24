
import { useEffect, useState, useRef } from "react";

export default function VeritasDashboard() {
  const [leanbots, setLeanbots] = useState({});
  const [trafficState, setTrafficState] = useState(null);
  const [connected, setConnected] = useState(false);

  const [frames, setFrames] = useState({
    TOPDOWN: null,
    FOOT: null
  });

  // Tracks which camera the next binary message belongs to
  const pendingCamera = useRef(null);

  // Tracks object URLs to prevent memory leaks
  const frameUrls = useRef({});

  useEffect(() => {
    console.log("[VERITAS] Initializing WebSocket...");

    const ws = new WebSocket("ws://127.0.0.1:8000/ws");

    // Receive JPEG frames as Blob objects
    ws.binaryType = "blob";

    ws.onopen = () => {
      console.log("[WS] Connected successfully");
      setConnected(true);
    };

    ws.onmessage = (event) => {

      // ==================================
      // JSON MESSAGE
      // ==================================

      if (typeof event.data === "string") {
        try {
          const message = JSON.parse(event.data);

          if (message.type === "state_snapshot") {
            setLeanbots(message.leanbots);
            setTrafficState(message.traffic_state);
          }

          else if (message.type === "frame") {
            pendingCamera.current = message.camera_id;
          }

        } catch (error) {
          console.error("[WS] JSON parsing error:", error);
        }

        return;
      }

      // ==================================
      // BINARY JPEG FRAME
      // ==================================

      if (event.data instanceof Blob) {

        const cameraId = pendingCamera.current;

        if (!cameraId) {
          console.warn("[WS] Frame received without camera metadata");
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
        frameUrls.current[cameraId] = newUrl + ".jpg";

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

    return () => {
      console.log("[VERITAS] Cleaning up WebSocket");

      ws.close();

      Object.values(frameUrls.current).forEach(url => {
        URL.revokeObjectURL(url);
      });

      frameUrls.current = {};
    };

  }, []);

  return (
    <div style={{ padding: "20px" }}>

      <h1>Veritas Monitoring</h1>

      <p>
        Connection: {connected ? "🟢 Connected" : "🔴 Disconnected"}
      </p>

      <p>
        Traffic: {trafficState ?? "Unknown"}
      </p>

      {/* ==================================
          LIVE CAMERA FEEDS
      ================================== */}

      <h2>Live Camera Feeds</h2>

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
        gap: "20px"
      }}>

        {["TOPDOWN", "FOOT"].map(cameraId => (

          <div
            key={cameraId}
            style={{
              background: "#1e293b",
              color: "white",
              padding: "15px",
              borderRadius: "10px"
            }}
          >

            <h3>{cameraId} CAMERA</h3>

            {frames[cameraId] ? (

              <img
                src={frames[cameraId]}
                alt={`${cameraId} camera`}
                style={{
                  width: "100%",
                  display: "block",
                  borderRadius: "8px"
                }}
              />

            ) : (

              <div style={{
                background: "#334155",
                height: "240px",
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                borderRadius: "8px"
              }}>
                Waiting for camera...
              </div>

            )}

          </div>

        ))}

      </div>

      {/* ==================================
          EXISTING LEANBOT STATE
      ================================== */}

      <h2>Leanbots</h2>

      <pre>
        {JSON.stringify(leanbots, null, 2)}
      </pre>

    </div>
  );
}
