// static/js/network.js
// Graph for BizRay company network.
// Requires COMPANY_ID, COMPANY_NAME, NETWORK_API_URL defined in the template.

(function () {
  if (typeof COMPANY_ID === "undefined" || typeof NETWORK_API_URL === "undefined") {
    return; // not on company page
  }

  const graphContainer = document.getElementById("company-graph");
  if (!graphContainer) return;

  // Get element references dynamically to handle tab system
  function getGraphLoader() {
    return document.getElementById("graph-loader");
  }

  function getNetworkHeaderLoader() {
    return document.getElementById("network-header-loader");
  }

  function showGraphLoader() {
    const graphLoader = getGraphLoader();
    if (graphLoader) {
      graphLoader.style.display = "block";
      console.log("Graph loader shown");
    } else {
      console.error("Graph loader element not found!");
    }
    // Show header spinner next to "Network" word
    const networkHeaderLoader = getNetworkHeaderLoader();
    if (networkHeaderLoader) {
      networkHeaderLoader.style.display = "inline-block";
      networkHeaderLoader.classList.add("show");
      console.log("Network header loader shown");
    } else {
      console.warn("Network header loader element not found - may not be in DOM yet");
    }
  }

  function hideGraphLoader() {
    const graphLoader = getGraphLoader();
    if (graphLoader) {
      graphLoader.style.display = "none";
      console.log("Graph loader hidden");
    }
    // Hide header spinner
    const networkHeaderLoader = getNetworkHeaderLoader();
    if (networkHeaderLoader) {
      networkHeaderLoader.style.display = "none";
      networkHeaderLoader.classList.remove("show");
      console.log("Network header loader hidden");
    }
  }

  const nodes = new vis.DataSet();
  const edges = new vis.DataSet();
  const seenNodes = new Set();

  let network = null;

  function showMessage(text) {
    const msgEl = document.getElementById("graph-message");
    if (msgEl) msgEl.textContent = text || "";
  }

  function clearMessage() {
    showMessage("");
  }

  function escapeHtml(str) {
    if (str == null) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }
  // function for formating numbers in the detail panel
  function formatEuroNumber(value) {
    if (value == null || isNaN(value)) return "not available";

    let formatted = Number(value).toFixed(2);
    formatted = formatted.replace(".", ",");
    formatted = formatted.replace(/\B(?=(\d{3})+(?!\d))/g, " ");

    return formatted;
  }

  function makeNodeId(type, key) {
    return `${type}:${key}`;
  }

  // Supports:
  // { "result": { "address_key": "..." } }
  // { "result": { "manager_key": "..." } }
  // { "result": "{\"company_id\": \"627820s\", ...}" }
  // Normalises one neighbour entry coming from the backend
  function parseNeighbour(neighbour) {
    if (!neighbour) return null;

    // Backend can return:
    // { result: { address_key: "..." } }
    // { result: { manager_key: "..." } }
    // { result: "{\"company_id\": \"154212h\", ...}" }  // glance JSON string
    // or sometimes just the payload itself.
    let payload = neighbour.connected ?? neighbour.result ?? neighbour;

    // --- STRING CASE: glance JSON or error text ---
    if (typeof payload === "string") {
      // Old backend error case, keep this just in case
      if (payload.includes("NoneType")) {
        return {
          type: "Address",
          key: "unknown_address",
          label: "Address unknown",
        };
      }

      // Try to parse glance JSON: {"company_id": "...", ...}
      try {
        const g = JSON.parse(payload);

        if (g && g.company_id) {
          const id = g.company_id;
          const name = g.company_name || id;
          const label = `${name}`; // show ONLY the name

          return {
            type: "Company",
            key: id,
            label: label,
            extra: {
              companyId: id,
              companyName: name,
              deleted: g.deleted,
              last_file: g.last_file,
              missing_years: g.missing_years,
              profit_loss: g.profit_loss,
            },
          };
        }

        // Unknown JSON shape – ignore
        return null;
      } catch (e) {
        // Random string we don't know – ignore
        return null;
      }
    }

    // --- ADDRESS NODE ---
    if (payload.address_key !== undefined) {
      const ak = payload.address_key;

      if (ak === null || ak === "" || (typeof ak === "string" && ak.includes("NoneType"))) {
        return {
          type: "Address",
          key: "unknown_address",
          label: "Address unknown",
        };
      }

      return {
        type: "Address",
        key: ak,
        label: ak,
      };
    }

    // --- MANAGER NODE ---
    if (payload.manager_key) {
      const parts = payload.manager_key.split("|");
      const date = parts[0] || "";
      const name = parts.slice(1).join("|") || payload.manager_key;
      return {
        type: "Manager",
        key: payload.manager_key,
        label: name,
        extra: { date: date },
      };
    }

    // --- COMPANY NODE AS FULL OBJECT (if backend ever returns it) ---
    if (payload.company_id) {
      return {
        type: "Company",
        key: payload.company_id,
        label: payload.company_id,
      };
    }

    // Fallback – ignore unknown shapes
    return null;
  }

  function addCentralCompanyNode() {
    const type = "Company";
    const key = COMPANY_ID;
    const nodeId = makeNodeId(type, key);

    if (!seenNodes.has(nodeId)) {
      const name = COMPANY_NAME || COMPANY_ID;
      const title = `Company\nName: ${name}\nID: ${COMPANY_ID}`;

      nodes.add({
        id: nodeId,
        label: name,
        group: "company",
        title: title,
        rawKey: COMPANY_ID,
        name: COMPANY_NAME
      });
      seenNodes.add(nodeId);
    }
    return nodeId;
  }

  function initNetwork() {
    const data = {nodes: nodes, edges: edges};
    const options = {
      interaction: {
        hover: true,
        zoomView: true,
        dragView: true,
        dragNodes: true
      },
      physics: {
        enabled: true,
        solver: "forceAtlas2Based",
        stabilization: {iterations: 150}
      },
      nodes: {
        font: {size: 14}
      },
      edges: {
        smooth: true
      },
      groups: {
        company: {
          shape: "dot",
          size: 25,
          color: {background: "#1f77b4", border: "#1f77b4"} // blue
        },
        manager: {
          shape: "dot",
          size: 20,
          color: {background: "#ff7f0e", border: "#ff7f0e"} // orange
        },
        address: {
          shape: "dot",
          size: 20,
          color: {background: "#2ca02c", border: "#2ca02c"} // green
        },
        unknown: {
          shape: "dot",
          size: 18,
          color: {background: "#7f7f7f", border: "#7f7f7f"} // grey
        }
      }
    };

    network = new vis.Network(graphContainer, data, options);

    // Click to expand, but NEVER show "no connections" from clicks
    network.on("click", function (params) {
      if (!params.nodes || params.nodes.length === 0) return;
      const nodeId = params.nodes[0];
      const [type, key] = nodeId.split(":");
      // expandNode will show the loader when fetching connections
      expandNode(type, key, false);
    });

    // Detail panel on select
    network.on("selectNode", function (params) {
      const nodeId = params.nodes[0];
      const node = nodes.get(nodeId);
      const panel = document.getElementById("node-detail");
      if (!panel || !node) return;

      const rawType = node.group || "";
      const prettyType =
        rawType.charAt(0).toUpperCase() + rawType.slice(1); // company -> Company

      if (rawType === "company") {
        panel.innerHTML = `
          <h5 class="network-detail-title">Selected Company</h5>
          <p><strong>Name:</strong> ${escapeHtml(node.label)}</p>
          <p><strong>FNR:</strong> ${escapeHtml(node.rawKey)}</p>
        `;
        if (node.extra) {
            panel.innerHTML += `
              <p><strong>Status:</strong>  ${node.extra.deleted === true ? "Not Active" :
                                              node.extra.deleted === false ? "Active" :
                                              "not available"
                                            }</p>
              <p><strong>Last filed XML:</strong> ${escapeHtml(node.extra.last_file || "not available")}</p>
              <p><strong>Missing years:</strong> ${node.extra.missing_years ?? "not available"}</p>
              <p><strong>Retained Earnings:</strong> ${node.extra.profit_loss != null ? formatEuroNumber(node.extra.profit_loss) : "not available"}</p>
            `;
          }
      } else {
        panel.innerHTML = `
          <h5 class="network-detail-title">Selected ${escapeHtml(prettyType)}</h5>
          <p><strong>Label:</strong> ${escapeHtml(node.label)}</p>
        `;
      }
    });
  }

  function fetchNeighbours(key, label) {
    const url = `${NETWORK_API_URL}?key=${encodeURIComponent(key)}&label=${encodeURIComponent(label)}`;
    return fetch(url).then(resp => {
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }
      return resp.json();
    });
  }

  // showEmptyMessageForThisNode = true ONLY for the initial company load
  function expandNode(type, key, showEmptyMessageForThisNode) {
     showGraphLoader();
    clearMessage();

    return fetchNeighbours(key, type)
      .then(data => {
        const neighbours = data.neighbours || [];

        // Only in ONE case do we show the message:
        // - this node is allowed to show it (flag true)
        // - backend returned no neighbours
        if (!neighbours.length) {
          if (showEmptyMessageForThisNode) {
            showMessage("No connections available for this company.");
          }
          return;
        }

        const sourceId = makeNodeId(type, key);
        let anyNew = false;

        neighbours.forEach(n => {
          const parsed = parseNeighbour(n);

          if (!parsed || !parsed.key) return;

          const targetNodeId = makeNodeId(parsed.type, parsed.key);

          if (!seenNodes.has(targetNodeId)) {
            const groupName = parsed.type.toLowerCase();
            let title = "";

            if (parsed.type === "Company") {
              const name = (parsed.extra && parsed.extra.companyName) ? parsed.extra.companyName : parsed.label;
              title = `Company\nName: ${name}\nID: ${parsed.key}`;
            }
            else if (parsed.type === "Manager") {
              title = `Manager\nName: ${parsed.label}`;
              if (parsed.extra && parsed.extra.date) {
                title += `\nDOB: ${parsed.extra.date}`;
              }
            } else if (parsed.type === "Address") {
              title = `Address\n${parsed.label}`;
            }
            else {
              // Address or unknown
              title = `${parsed.type}\n${parsed.label}`;
            }

            nodes.add({
              id: targetNodeId,
              label: parsed.label,
              group:
                groupName === "company" ||
                groupName === "manager" ||
                groupName === "address"
                  ? groupName
                  : "unknown",
              title: title,           // <-- now correct per type
              rawKey: parsed.key,     // <-- ID for detail panel only
              name: parsed.label,
              extra: parsed.extra || {}
            });

            seenNodes.add(targetNodeId);
            anyNew = true;
          }

          // undirected-looking edge, no arrows, avoid duplicate ID direction issues
          const edgeId = [sourceId, targetNodeId].sort().join("<->");
          if (!edges.get(edgeId)) {
            edges.add({
              id: edgeId,
              from: sourceId,
              to: targetNodeId
            });
          }
        });

        // No message here even if nothing new was added.
      // Backend had neighbours but nothing new got added => tell user
      if (!anyNew && showEmptyMessageForThisNode) {
        showMessage("No further connections for this node.");
      }
    })
    .catch(err => {
      console.error("Error expanding node", err);
      if (showEmptyMessageForThisNode) {
        showMessage("No further connections for this node.");
      }
    })
    .finally(() => {
      hideGraphLoader();  // ← HIDE SPINNER
    });
  }

  function initialLoad() {
    // Show loader immediately when starting to load the graph
    showGraphLoader();
    
    // Use setTimeout to ensure loader is visible before network initialization
    setTimeout(() => {
      addCentralCompanyNode();
      initNetwork();

      // First and ONLY time we allow the "no connections" message.
      // expandNode will keep the loader visible while fetching
      expandNode("Company", COMPANY_ID, true);
    }, 50);
  }

  // Script is loaded after the DOM elements in the template.
  // Wait for DOM to be fully ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialLoad);
  } else {
    initialLoad();
  }
})();


