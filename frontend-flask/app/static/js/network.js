// static/js/network.js
// Graph for BizRay company network.
// Requires COMPANY_ID, COMPANY_NAME, NETWORK_API_URL defined in the template.

(function () {
  if (typeof COMPANY_ID === "undefined" || typeof NETWORK_API_URL === "undefined") {
    return; // not on company page
  }

  const graphContainer = document.getElementById("company-graph");
  if (!graphContainer) return;

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

  function makeNodeId(type, key) {
    return `${type}:${key}`;
  }

  // Supports:
  // { "result": { "address_key": "..." } }
  // { "result": { "manager_key": "..." } }
  // { "result": "{\"company_id\": \"627820s\", ...}" }
  function parseNeighbour(neighbour) {
    if (!neighbour) return null;

    let payload = neighbour.connected || neighbour.result || null;
    if (!payload) return null;

    if (typeof payload === "string") {
      try {
        payload = JSON.parse(payload);
      } catch (e) {
        return {
          type: "Unknown",
          key: payload,
          label: payload
        };
      }
    }

    if (payload.address_key) {
      return {
        type: "Address",
        key: payload.address_key,
        label: payload.address_key
      };
    }

    if (payload.manager_key) {
      const parts = payload.manager_key.split("|");
      const date = parts[0] || "";
      const name = parts.slice(1).join("|") || payload.manager_key;
      return {
        type: "Manager",
        key: payload.manager_key,
        label: name,
        extra: { date: date }
      };
    }

    if (payload.company_id) {
      return {
        type: "Company",
        key: payload.company_id,
        label: payload.company_id
      };
    }

    const firstKey = Object.keys(payload)[0];
    const val = payload[firstKey];
    return {
      type: "Unknown",
      key: String(val),
      label: String(val)
    };
  }

  function addCentralCompanyNode() {
    const type = "Company";
    const key = COMPANY_ID;
    const nodeId = makeNodeId(type, key);

    if (!seenNodes.has(nodeId)) {
      nodes.add({
        id: nodeId,
        label: COMPANY_NAME || COMPANY_ID,
        group: "company",
        title: `Company\nID: ${COMPANY_ID}`
      });
      seenNodes.add(nodeId);
    }
    return nodeId;
  }

  function initNetwork() {
    const data = { nodes: nodes, edges: edges };
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
        stabilization: { iterations: 150 }
      },
      nodes: {
        font: { size: 14 }
      },
      edges: {
        smooth: true
      },
      groups: {
        company: {
          shape: "dot",
          size: 25,
          color: { background: "#1f77b4", border: "#1f77b4" } // blue
        },
        manager: {
          shape: "dot",
          size: 20,
          color: { background: "#ff7f0e", border: "#ff7f0e" } // orange
        },
        address: {
          shape: "dot",
          size: 20,
          color: { background: "#2ca02c", border: "#2ca02c" } // green
        },
        unknown: {
          shape: "dot",
          size: 18,
          color: { background: "#7f7f7f", border: "#7f7f7f" } // grey
        }
      }
    };

    network = new vis.Network(graphContainer, data, options);

    // Click to expand, but NEVER show "no connections" from clicks
    network.on("click", function (params) {
      if (!params.nodes || params.nodes.length === 0) return;
      const nodeId = params.nodes[0];
      const [type, key] = nodeId.split(":");
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


      panel.innerHTML = `
        <h5 class="network-detail-title">Selected ${escapeHtml(prettyType)}</h5>
        <p><strong>Label:</strong> ${escapeHtml(node.label)}</p>
      `;
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

        neighbours.forEach(n => {
          const parsed = parseNeighbour(n);
          if (!parsed || !parsed.key) return;

          const targetNodeId = makeNodeId(parsed.type, parsed.key);

          if (!seenNodes.has(targetNodeId)) {
            const groupName = parsed.type.toLowerCase();
            let title = `${parsed.type}\n${parsed.label}`;
            if (parsed.type === "Manager" && parsed.extra && parsed.extra.date) {
              title += `\nDOB: ${parsed.extra.date}`;
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
              title: title
            });
            seenNodes.add(targetNodeId);
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
      })
      .catch(err => {
        console.error("Error expanding node", err);
        if (showEmptyMessageForThisNode) {
          showMessage("No connections available for this company.");
        }
      });
  }

  function initialLoad() {
    addCentralCompanyNode();
    initNetwork();

    // First and ONLY time we allow the "no connections" message.
    expandNode("Company", COMPANY_ID, true);
  }

  // Script is loaded after the DOM elements in the template.
  initialLoad();
})();
