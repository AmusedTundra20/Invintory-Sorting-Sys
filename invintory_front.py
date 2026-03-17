import json
import requests
import streamlit as st
import streamlit.components.v1 as components

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


if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "scanned_barcode" not in st.session_state:
    st.session_state.scanned_barcode = ""

if "barcode_input" not in st.session_state:
    st.session_state.barcode_input = ""


st.title("Inventory Sorting System")
st.caption("Streamlit frontend with ZXing-JS camera barcode scanner")

with st.sidebar:
    st.header("Backend Settings")
    api_base = st.text_input("Backend API URL", value=DEFAULT_API_BASE)
    if st.button("Refresh Inventory"):
        st.rerun()

left, right = st.columns([1.15, 1])

with left:
    st.subheader("Camera Barcode Scanner")

    scanner_html = """
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8" />
      <script type="module">
        import { BrowserMultiFormatReader } from 'https://cdn.jsdelivr.net/npm/@zxing/browser@0.1.5/+esm';

        let codeReader = null;
        let controls = null;

        async function startScanner() {
          const status = document.getElementById("status");
          const resultBox = document.getElementById("result");

          try {
            codeReader = new BrowserMultiFormatReader();
            const videoInputDevices = await BrowserMultiFormatReader.listVideoInputDevices();

            if (!videoInputDevices.length) {
              status.innerText = "No camera found.";
              return;
            }

            const selectedDeviceId = videoInputDevices[0].deviceId;
            status.innerText = "Starting camera...";

            controls = await codeReader.decodeFromVideoDevice(
              selectedDeviceId,
              'video',
              (result, error) => {
                if (result) {
                  const text = result.getText();
                  resultBox.innerText = text;
                  status.innerText = "Barcode detected.";

                  const streamlitData = {
                    isStreamlitMessage: true,
                    type: "streamlit:setComponentValue",
                    value: text
                  };
                  window.parent.postMessage(streamlitData, "*");
                }
              }
            );

            status.innerText = "Scanner running.";
          } catch (err) {
            status.innerText = "Camera error: " + err;
          }
        }

        function stopScanner() {
          const status = document.getElementById("status");
          try {
            if (controls) {
              controls.stop();
            }
            if (codeReader) {
              codeReader.reset();
            }
            status.innerText = "Scanner stopped.";
          } catch (err) {
            status.innerText = "Stop error: " + err;
          }
        }

        window.startScanner = startScanner;
        window.stopScanner = stopScanner;
      </script>
      <style>
        body {
          font-family: Arial, sans-serif;
          margin: 0;
          padding: 0.75rem;
          background: white;
        }
        .wrap {
          border: 1px solid #ddd;
          border-radius: 12px;
          padding: 12px;
        }
        video {
          width: 100%;
          max-height: 320px;
          border-radius: 10px;
          background: black;
        }
        .row {
          display: flex;
          gap: 10px;
          margin-top: 10px;
          flex-wrap: wrap;
        }
        button {
          padding: 10px 14px;
          border: none;
          border-radius: 10px;
          cursor: pointer;
          font-weight: 600;
        }
        .start { background: #d1fae5; }
        .stop { background: #fee2e2; }
        .box {
          margin-top: 10px;
          padding: 10px;
          border-radius: 10px;
          background: #f8fafc;
          border: 1px solid #e5e7eb;
          word-break: break-all;
        }
      </style>
    </head>
    <body>
      <div class="wrap">
        <video id="video"></video>
        <div class="row">
          <button class="start" onclick="startScanner()">Start Camera</button>
          <button class="stop" onclick="stopScanner()">Stop Camera</button>
        </div>
        <div class="box"><strong>Status:</strong> <span id="status">Idle</span></div>
        <div class="box"><strong>Detected Barcode:</strong> <span id="result">None</span></div>
      </div>
    </body>
    </html>
    """

    scanned_value = components.html(scanner_html, height=520)

    if scanned_value:
        st.session_state.scanned_barcode = scanned_value
        st.session_state.barcode_input = scanned_value
        st.success(f"Scanned barcode: {scanned_value}")

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