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

  // Expand / collapse state (frontend only)
  const expandedNodes = new Set();        // nodeId
  const expansionRecords = new Map();     // nodeId -> { addedNodeIds:Set, addedEdgeIds:Set }

  // Expandability probing cache
  const expandabilityChecked = new Set(); // nodeId
  const expandabilityPending = new Set(); // nodeId

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

  function companyLabel(name, risk) {
    const r = (risk === "H" || risk === "M" || risk === "L") ? risk : "";
    if (!r) return escapeHtml(name);
    return `${escapeHtml(name)}\n<b>${r}</b>`;
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

  function fetchNeighbours(key, label) {
    const url = `${NETWORK_API_URL}?key=${encodeURIComponent(key)}&label=${encodeURIComponent(label)}`;
    return fetch(url).then(resp => {
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }
      return resp.json();
    });
  }

  // Apply border ONLY when node is expandable. Preserve group background color.
  function applyExpandableBorder(nodeId) {
    const node = nodes.get(nodeId);
    if (!node) return;

    const groupColors = {
      company: "#1f77b4",
      manager: "#ff7f0e",
      address: "#2ca02c",
      unknown: "#7f7f7f"
    };

    const g = (node.group || "unknown").toLowerCase();
    const bg = groupColors[g] || groupColors.unknown;

    nodes.update({
      id: nodeId,
      isExpandable: true,
      borderWidth: 4,
      borderWidthSelected: 4,
      color: {
        background: bg,
        border: "#000000",
        highlight: { background: bg, border: "#000000" }
      }
    });
  }

  function markNotExpandable(nodeId) {
    const node = nodes.get(nodeId);
    if (!node) return;
    nodes.update({ id: nodeId, isExpandable: false });
  }

  // Supports:
  // { "result": { "address_key": "..." } }
  // { "result": { "manager_key": "..." } }
  // { "result": "{\"company_id\": \"627820s\", ...}" }
  // Normalises one neighbour entry coming from the backend
  function parseNeighbour(neighbour) {
    if (!neighbour) return null;

    let payload = neighbour.connected ?? neighbour.result ?? neighbour;

    // --- STRING CASE: glance JSON or error text ---
    if (typeof payload === "string") {
      if (payload.includes("NoneType")) {
        return {
          type: "Address",
          key: "unknown_address",
          label: "Address unknown",
        };
      }

      try {
        const g = JSON.parse(payload);

        if (g && g.company_id) {
          const id = g.company_id;
          const name = g.company_name || id;
          const risk = g.risk_level || null;

          return {
            type: "Company",
            key: id,
            label: companyLabel(name, risk),
            extra: {
              companyId: id,
              companyName: name,
              deleted: g.deleted,
              last_file: g.last_file,
              missing_years: g.missing_years,
              profit_loss: g.profit_loss,
              risk_level: risk
            },
          };
        }

        return null;
      } catch (e) {
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
      const id = payload.company_id;
      const name = payload.company_name || id;
      const risk = payload.risk_level || null;
      return {
        type: "Company",
        key: id,
        label: companyLabel(name, risk),
        extra: {
          companyId: id,
          companyName: name,
          risk_level: risk
        }
      };
    }

    return null;
  }

  // Probe backend once to decide if node is expandable.
  // IMPORTANT: expandable means it would add at least one NEW node (not already in seenNodes).
  // Returns Promise<boolean>.
  function checkExpandable(type, key) {
    const nodeId = makeNodeId(type, key);

    if (expandabilityChecked.has(nodeId)) {
      const node = nodes.get(nodeId);
      return Promise.resolve(!!(node && node.isExpandable));
    }

    if (expandabilityPending.has(nodeId)) {
      return new Promise(resolve => {
        const t = setInterval(() => {
          if (!expandabilityPending.has(nodeId)) {
            clearInterval(t);
            const node = nodes.get(nodeId);
            resolve(!!(node && node.isExpandable));
          }
        }, 60);
      });
    }

    expandabilityPending.add(nodeId);

    return fetchNeighbours(key, type)
      .then(data => {
        const neighbours = (data && data.neighbours) ? data.neighbours : [];

        // Decide if ANY neighbour would be a NEW node on the graph
        let wouldAddNew = false;
        if (Array.isArray(neighbours)) {
          for (const n of neighbours) {
            const parsed = parseNeighbour(n);
            if (!parsed || !parsed.key) continue;

            const targetNodeId = makeNodeId(parsed.type, parsed.key);
            if (!seenNodes.has(targetNodeId)) {
              wouldAddNew = true;
              break;
            }
          }
        }

        expandabilityChecked.add(nodeId);

        if (wouldAddNew) {
          applyExpandableBorder(nodeId);
          return true;
        } else {
          markNotExpandable(nodeId);
          return false;
        }
      })
      .catch(() => {
        expandabilityChecked.add(nodeId);
        markNotExpandable(nodeId);
        return false;
      })
      .finally(() => {
        expandabilityPending.delete(nodeId);
      });
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
        label: companyLabel(name, (typeof COMPANY_RISK_LEVEL !== "undefined" ? COMPANY_RISK_LEVEL : null)),
        group: "company",
        title: title,
        rawKey: COMPANY_ID,
        name: COMPANY_NAME || name,
        extra: {
          companyId: COMPANY_ID,
          companyName: name,
          risk_level: (typeof COMPANY_RISK_LEVEL !== "undefined" ? COMPANY_RISK_LEVEL : null)
        },
        isExpandable: false
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
        font: {size: 14, multi: "html"}
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

    // Click toggle:
    // - if expanded -> collapse
    // - if expandable -> expand
    // - if not expandable -> do nothing (selection still works)
    network.on("click", function (params) {
      if (!params.nodes || params.nodes.length === 0) return;
      const nodeId = params.nodes[0];
      const [type, key] = nodeId.split(":");
      const node = nodes.get(nodeId);
      if (!node) return;

      // AUTO-ENRICH when clicking a company
      if (type === "Company") {
        fetch(`http://127.0.0.1:8000/enrich/neighbours/${encodeURIComponent(key)}`, {
          method: "POST",
        })
        .then(() => {
          expandNode(type, key, true);
        })
        .catch(() => {});
      }

      if (expandedNodes.has(nodeId)) {
        collapseNode(nodeId);
        return;
      }

      if (node.isExpandable) {
        expandNode(type, key, true);
      }
    });


    // Detail panel on select (OG)
    network.on("selectNode", function (params) {
      const nodeId = params.nodes[0];
      const node = nodes.get(nodeId);
      const panel = document.getElementById("node-detail");
      if (!panel || !node) return;

      const rawType = node.group || "";
      const prettyType =
        rawType.charAt(0).toUpperCase() + rawType.slice(1); // company -> Company

      if (rawType === "company") {
        const rawRisk = node.extra?.risk_level;
        const riskVal =
          rawRisk && String(rawRisk).trim() && String(rawRisk).trim().toUpperCase() !== "NONE"
            ? String(rawRisk).trim().toUpperCase()
            : "No risk data available";

        panel.innerHTML = `
          <h5 class="network-detail-title">Selected Company</h5>
          <p><strong>Name:</strong> ${escapeHtml(node.extra?.companyName || node.name || "")}</p>
          <p><strong>Risk:</strong> ${escapeHtml(riskVal)}</p>
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

  // Expand node and also check expandability for newly shown nodes.
  // Loader hides only after border checks finish.
  function expandNode(type, key, showEmptyMessageForThisNode) {
    showGraphLoader();
    clearMessage();

    const sourceId = makeNodeId(type, key);

    return fetchNeighbours(key, type)
      .then(data => {
        const neighbours = data.neighbours || [];

        if (!neighbours.length) {
          if (showEmptyMessageForThisNode) {
            showMessage("No connections available for this company.");
          }
          // if no neighbours, cannot add new nodes
          expandabilityChecked.add(sourceId);
          markNotExpandable(sourceId);
          return [];
        }

        // Expanding succeeded; recompute expandability of source based on "adds new nodes"
        // For the source itself, if this call returned neighbours, it is expandable by definition of user action.
        // Still, we keep border consistent:
        applyExpandableBorder(sourceId);
        expandabilityChecked.add(sourceId);

        let anyNew = false;

        const record = { addedNodeIds: new Set(), addedEdgeIds: new Set() };
        const expandChecks = [];

        neighbours.forEach(n => {
          const parsed = parseNeighbour(n);
          if (!parsed || !parsed.key) return;

          const targetNodeId = makeNodeId(parsed.type, parsed.key);

          // refresh existing company nodes after enrichment (risk/label changes)
          if (seenNodes.has(targetNodeId) && parsed.type === "Company") {
            nodes.update({
              id: targetNodeId,
              label: parsed.label,
              extra: parsed.extra || {},
              name: parsed.label
            });
          }

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
              title: title,
              rawKey: parsed.key,
              name: parsed.label,
              extra: parsed.extra || {},
              isExpandable: false
            });

            seenNodes.add(targetNodeId);
            record.addedNodeIds.add(targetNodeId);
            anyNew = true;

            // check whether this new node would add MORE nodes beyond what's already visible
            expandChecks.push(checkExpandable(parsed.type, parsed.key));
          }

          const edgeId = [sourceId, targetNodeId].sort().join("<->");
          if (!edges.get(edgeId)) {
            edges.add({
              id: edgeId,
              from: sourceId,
              to: targetNodeId
            });
            record.addedEdgeIds.add(edgeId);
          }
        });

        expandedNodes.add(sourceId);
        expansionRecords.set(sourceId, record);

        if (!anyNew && showEmptyMessageForThisNode) {
          showMessage("No further connections for this node.");
        }

        return Promise.all(expandChecks);
      })
      .catch(err => {
        console.error("Error expanding node", err);
        if (showEmptyMessageForThisNode) {
          showMessage("No further connections for this node.");
        }
      })
      .finally(() => {
        hideGraphLoader();
      });
  }

  function nodeHasAnyEdges(nodeId) {
    const allEdges = edges.get();
    for (const e of allEdges) {
      if (e.from === nodeId || e.to === nodeId) return true;
    }
    return false;
  }

  function collapseNode(nodeId) {
    const rec = expansionRecords.get(nodeId);
    if (!rec) {
      expandedNodes.delete(nodeId);
      return;
    }

    rec.addedEdgeIds.forEach(edgeId => {
      if (edges.get(edgeId)) edges.remove(edgeId);
    });

    rec.addedNodeIds.forEach(nid => {
      if (!nodes.get(nid)) return;

      if (!nodeHasAnyEdges(nid)) {
        nodes.remove(nid);
        seenNodes.delete(nid);

        expandedNodes.delete(nid);
        expansionRecords.delete(nid);

        // allow re-check if it reappears later
        expandabilityChecked.delete(nid);
        expandabilityPending.delete(nid);
      }
    });

    expandedNodes.delete(nodeId);
    expansionRecords.delete(nodeId);
  }

  function initialLoad() {
    showGraphLoader();

    setTimeout(() => {
      addCentralCompanyNode();
      initNetwork();

      // 🔹 AUTO-ENRICH CENTRAL COMPANY ON LOAD
      fetch(`http://127.0.0.1:8000/enrich/neighbours/${encodeURIComponent(COMPANY_ID)}`, {
        method: "POST",
      })
      .then(() => refreshCompanyNode(COMPANY_ID))
      .catch(() => {});

      // Initial expand
      expandNode("Company", COMPANY_ID, true);
    }, 50);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialLoad);
  } else {
    initialLoad();
  }
})();