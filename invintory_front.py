import requests
import streamlit as st

st.set_page_config(page_title="Inventory Sorting System", layout="wide")

DEFAULT_API_BASE = "http://127.0.0.1:8000"


def get_items(api_base: str):
    response = requests.get(f"{api_base}/items", timeout=5)
    response.raise_for_status()
    return response.json()


def submit_scan(api_base: str, payload: dict):
    response = requests.post(f"{api_base}/scan", json=payload, timeout=5)
    data = response.json()
    if response.status_code >= 400:
        raise Exception(data.get("detail", "Scan failed"))
    return data


def create_item(api_base: str, payload: dict):
    response = requests.post(f"{api_base}/items", json=payload, timeout=5)
    data = response.json()
    if response.status_code >= 400:
        raise Exception(data.get("detail", "Could not create item"))
    return data


def delete_item(api_base: str, barcode: str):
    response = requests.delete(f"{api_base}/items/{barcode}", timeout=5)
    data = response.json()
    if response.status_code >= 400:
        raise Exception(data.get("detail", "Could not delete item"))
    return data


def get_component_value(result, name, default=None):
    if result is None:
        return default
    if isinstance(result, dict):
        return result.get(name, default)
    return getattr(result, name, default)


if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "barcode_input" not in st.session_state or not isinstance(st.session_state.barcode_input, str):
    st.session_state.barcode_input = ""

if "last_scanned_barcode" not in st.session_state:
    st.session_state.last_scanned_barcode = ""

if "scanner_status" not in st.session_state:
    st.session_state.scanner_status = "Idle"


# ---- Proper custom component using Streamlit Components v2 ----
SCANNER_HTML = """
<div class="scanner-wrap">
  <video id="zxing-video" playsinline muted></video>
  <div class="scanner-buttons">
    <button id="zxing-start" type="button">Start Camera</button>
    <button id="zxing-stop" type="button">Stop Camera</button>
  </div>
  <div class="scanner-box"><strong>Status:</strong> <span id="zxing-status">Idle</span></div>
  <div class="scanner-box"><strong>Detected Barcode:</strong> <span id="zxing-result">None</span></div>
</div>
"""

SCANNER_CSS = """
.scanner-wrap {
  border: 1px solid #ddd;
  border-radius: 12px;
  padding: 12px;
  background: white;
}
#zxing-video {
  width: 100%;
  max-height: 360px;
  border-radius: 10px;
  background: black;
}
.scanner-buttons {
  display: flex;
  gap: 10px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.scanner-buttons button {
  padding: 10px 14px;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 600;
}
#zxing-start {
  background: #d1fae5;
}
#zxing-stop {
  background: #fee2e2;
}
.scanner-box {
  margin-top: 10px;
  padding: 10px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  word-break: break-all;
}
"""

SCANNER_JS = """
export default function(component) {
  const { parentElement, setStateValue, setTriggerValue } = component;

  const video = parentElement.querySelector("#zxing-video");
  const startBtn = parentElement.querySelector("#zxing-start");
  const stopBtn = parentElement.querySelector("#zxing-stop");
  const statusEl = parentElement.querySelector("#zxing-status");
  const resultEl = parentElement.querySelector("#zxing-result");

  if (!video || !startBtn || !stopBtn || !statusEl || !resultEl) {
    return;
  }

  if (parentElement.__zxing_initialized) {
    return parentElement.__zxing_cleanup || (() => {});
  }
  parentElement.__zxing_initialized = true;

  let codeReader = null;
  let controls = null;

  const setStatus = (text) => {
    statusEl.textContent = text;
    setStateValue("status", text);
  };

  const stopScanner = async () => {
    try {
      if (controls && typeof controls.stop === "function") {
        controls.stop();
      }
      if (codeReader && typeof codeReader.reset === "function") {
        codeReader.reset();
      }
      controls = null;
      codeReader = null;
      setStatus("Scanner stopped.");
    } catch (err) {
      setStatus("Stop error: " + err);
    }
  };

  const startScanner = async () => {
    try {
      setStatus("Loading ZXing...");

      const { BrowserMultiFormatReader } = await import("https://cdn.jsdelivr.net/npm/@zxing/browser@0.1.5/+esm");

      codeReader = new BrowserMultiFormatReader();

      const devices = await BrowserMultiFormatReader.listVideoInputDevices();
      if (!devices || devices.length === 0) {
        setStatus("No camera found.");
        return;
      }

      const selectedDeviceId = devices[0].deviceId;
      setStatus("Starting camera...");

      controls = await codeReader.decodeFromVideoDevice(
        selectedDeviceId,
        video,
        (result, error) => {
          if (result) {
            const text = result.getText();
            resultEl.textContent = text;

            setStateValue("barcode", text);
            setTriggerValue("scan_event", Date.now());
            setStatus("Barcode detected.");

            stopScanner();
          } else if (error && error.name !== "NotFoundException") {
            console.error(error);
          }
        }
      );

      setStatus("Scanner running.");
    } catch (err) {
      console.error(err);
      setStatus("Camera error: " + err);
    }
  };

  startBtn.addEventListener("click", startScanner);
  stopBtn.addEventListener("click", stopScanner);

  parentElement.__zxing_cleanup = () => {
    startBtn.removeEventListener("click", startScanner);
    stopBtn.removeEventListener("click", stopScanner);
    stopScanner();
  };

  return parentElement.__zxing_cleanup;
}
"""

try:
    zxing_scanner = st.components.v2.component(
        "zxing_barcode_scanner",
        html=SCANNER_HTML,
        css=SCANNER_CSS,
        js=SCANNER_JS,
    )
except AttributeError:
    st.error(
        "Your Streamlit version is too old for this scanner component. "
        "Run: pip install --upgrade streamlit"
    )
    st.stop()


st.title("Inventory Sorting System")
st.caption("Streamlit frontend with a proper ZXing-JS scanner component")

with st.sidebar:
    st.header("Backend Settings")
    api_base = st.text_input("Backend API URL", value=DEFAULT_API_BASE)
    if st.button("Refresh Inventory"):
        st.rerun()

left, right = st.columns([1.15, 1])

with left:
    st.subheader("Camera Barcode Scanner")

    scanner_result = zxing_scanner(
        on_scan_event_change=lambda: None,
        on_status_change=lambda: None,
    )

    scanned_barcode = get_component_value(scanner_result, "barcode", "")
    scanner_status = get_component_value(scanner_result, "status", "Idle")

    if isinstance(scanned_barcode, str) and scanned_barcode:
        if scanned_barcode != st.session_state.last_scanned_barcode:
            st.session_state.last_scanned_barcode = scanned_barcode
            st.session_state.barcode_input = scanned_barcode

    st.info(f"Scanner status: {scanner_status}")

    st.divider()
    st.subheader("Scan Item")

    barcode = st.text_input("Barcode", key="barcode_input")
    action = st.selectbox("Action", ["SORT", "IN", "OUT"])
    quantity = st.number_input("Quantity", min_value=1, step=1, value=1)
    source = st.text_input("Source", value="streamlit-app-1")
    location_hint = st.text_input("Location Hint", value="A")

    if st.button("Submit Scan", use_container_width=True):
        try:
            if not barcode.strip():
                st.error("Enter or scan a barcode first.")
            else:
                result = submit_scan(
                    api_base,
                    {
                        "barcode": barcode.strip(),
                        "action": action,
                        "quantity": int(quantity),
                        "source": source.strip() or "streamlit-app-1",
                        "location_hint": location_hint.strip() or None,
                    },
                )
                st.session_state.last_result = result
                st.success(result.get("message", "Scan completed."))
                st.rerun()
        except Exception as e:
            st.error(str(e))

    st.divider()
    st.subheader("Add Item")

    with st.form("add_item_form"):
        new_barcode = st.text_input("New Item Barcode")
        new_name = st.text_input("Item Name")
        new_category = st.text_input("Category")
        new_quantity = st.number_input("Starting Quantity", min_value=0, step=1, value=0)
        new_default_bin = st.text_input("Default Bin", value="BIN-A1")
        add_submitted = st.form_submit_button("Add Item", use_container_width=True)

        if add_submitted:
            try:
                create_item(
                    api_base,
                    {
                        "barcode": new_barcode.strip(),
                        "name": new_name.strip(),
                        "category": new_category.strip(),
                        "quantity": int(new_quantity),
                        "default_bin": new_default_bin.strip(),
                    },
                )
                st.success("Item added successfully.")
                st.rerun()
            except Exception as e:
                st.error(str(e))

with right:
    st.subheader("Last Scan Result")
    if st.session_state.last_result:
        st.json(st.session_state.last_result)
    else:
        st.info("No scan submitted yet.")

st.divider()
st.subheader("Inventory Items")

try:
    items = get_items(api_base)

    if not items:
        st.info("No items found.")
    else:
        for item in items:
            with st.container(border=True):
                row1, row2 = st.columns([4, 1])
                with row1:
                    st.markdown(f"**{item['name']}**")
                    st.write(f"Barcode: {item['barcode']}")
                    st.write(f"Category: {item['category']}")
                    st.write(f"Quantity: {item['quantity']}")
                    st.write(f"Default Bin: {item['default_bin']}")
                with row2:
                    if st.button("Delete", key=f"delete_{item['barcode']}", use_container_width=True):
                        try:
                            delete_item(api_base, item["barcode"])
                            st.success(f"Deleted {item['name']}")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
except Exception as e:
    st.error(f"Could not load inventory: {e}")