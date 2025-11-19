

(function() {
    'use strict';

    const companyContainer = document.getElementById('company-profile-container');
    if (!companyContainer) return;

    const fnr = companyContainer.getAttribute('data-fnr');
    if (!fnr) {
        showError('Company number not specified');
        return;
    }

  
    if (companyContainer.getAttribute('data-requires-auth') === 'true') {
        showAuthRequired();
        return;
    }

    loadCompanyData(fnr);

    
    function loadCompanyData(fnr) {
        showLoading();

        fetch(`/api/company/${encodeURIComponent(fnr)}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin'
        })
        .then(response => {
            if (response.status === 401) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Unauthorized');
                });
            }
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Failed to load company data');
                });
            }
            return response.json();
        })
        .then(data => {
            hideLoading();
            // Handle result wrapper
            const companyData = data.result || data;
            renderCompanyData(companyData);
        })
        .catch(error => {
            hideLoading();
            showError(error.message || 'An error occurred while loading company data');
            console.error('Error loading company:', error);
        });
    }

 
    function showLoading() {
        const container = document.getElementById('company-profile-container');
        container.innerHTML = `
            <div class="loading-state text-center" style="padding: 60px 20px;">
                <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-3" style="font-size: 1.1rem; color: #666;">Loading company information...</p>
            </div>
        `;
    }


    function hideLoading() {
      
    }

 
    function showError(message) {
        const container = document.getElementById('company-profile-container');
        container.innerHTML = `
            <div class="error-state" style="padding: 40px 20px;">
                <div class="alert alert-danger" role="alert">
                    <h4 class="alert-heading"><i class="fa fa-exclamation-triangle"></i> Error</h4>
                    <p>${escapeHtml(message)}</p>
                    <hr>
                    <p class="mb-0">
                        <button class="btn btn-primary" onclick="location.reload()">
                            <i class="fa fa-refresh"></i> Try Again
                        </button>
                        <a href="/search_results" class="btn btn-secondary ms-2">
                            <i class="fa fa-arrow-left"></i> Back to Search
                        </a>
                    </p>
                </div>
            </div>
        `;
    }


    function showAuthRequired() {
        const container = document.getElementById('company-profile-container');
        container.innerHTML = `
            <div class="auth-required-state" style="padding: 40px 20px;">
                <div class="alert alert-warning" role="alert">
                    <h4 class="alert-heading"><i class="fa fa-lock"></i> Authentication Required</h4>
                    <p>You must be logged in to view company details.</p>
                    <hr>
                    <p class="mb-0">
                        <a href="/login" class="btn btn-primary">
                            <i class="fa fa-sign-in"></i> Log In
                        </a>
                        <a href="/" class="btn btn-secondary ms-2">
                            <i class="fa fa-home"></i> Go to Home
                        </a>
                    </p>
                </div>
            </div>
        `;
    }


    function renderCompanyData(data) {
        const container = document.getElementById('company-profile-container');
        const basicInfo = data.basic_info || {};
        const location = data.location || {};
        const management = data.management || [];
        const financial = data.financial || {};
        const history = data.history || [];

        const locationParts = [];
        if (location.street && Array.isArray(location.street)) {
            locationParts.push(...location.street);
        }
        if (location.house_number) locationParts.push(location.house_number);
        if (location.postal_code) locationParts.push(location.postal_code);
        if (location.city) locationParts.push(location.city);
        if (location.country) locationParts.push(location.country);
        const locationStr = locationParts.join(', ') || 'N/A';

        const formatDate = (dateStr) => {
            if (!dateStr || dateStr.length !== 8 || !/^\d+$/.test(dateStr)) return dateStr || 'N/A';
            return `${dateStr.substring(6, 8)}.${dateStr.substring(4, 6)}.${dateStr.substring(0, 4)}`;
        };

        let html = `
            <div class="company-detail-card" style="background-color: #f7f7f7; border-radius: 7px; padding: 40px; margin-bottom: 30px;">
              
              <!-- Basic Information -->
              <div class="section mb-4">
                <h3 class="mb-3"><i class="fa fa-building"></i> Basic Information</h3>
                <div class="row">
                  <div class="col-md-6">
                    <p><strong>Company Name:</strong> ${escapeHtml(basicInfo.company_name || 'N/A')}</p>
                    <p><strong>Legal Form:</strong> ${escapeHtml(basicInfo.legal_form || 'N/A')}</p>
                  </div>
                  <div class="col-md-6">
                    <p><strong>Company Number:</strong> ${escapeHtml(basicInfo.company_number || 'N/A')}</p>
                    <p><strong>European ID:</strong> ${escapeHtml(basicInfo.european_id || 'N/A')}</p>
                  </div>
                </div>
              </div>

              <!-- Location Information -->
              <div class="section mb-4">
                <h3 class="mb-3"><i class="fa fa-map-marker"></i> Location</h3>
                <div class="row">
                  <div class="col-md-12">
                    <p>${escapeHtml(locationStr)}</p>
                  </div>
                </div>
              </div>

              <!-- Financial Information -->
              <div class="section mb-4">
                <h3 class="mb-3"><i class="fa fa-euro"></i> Financial Information</h3>
                <div class="row">
                  <div class="col-md-6">
                    ${financial.director_name ? `<p><strong>Director Name:</strong> ${escapeHtml(financial.director_name)}</p>` : ''}
                  </div>
                  <div class="col-md-6">
                    ${financial.total_assets ? `<p><strong>Total Assets:</strong> €${parseFloat(financial.total_assets).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</p>` : ''}
                  </div>
                </div>
                ${!financial.director_name && !financial.total_assets ? '<p class="text-muted">No financial information available.</p>' : ''}
              </div>
        `;

   
        if (management.length > 0) {
            html += `
              <div class="section mb-4">
                <h3 class="mb-3"><i class="fa fa-users"></i> Management</h3>
                <div class="table-responsive">
                  <table class="table table-striped">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Date of Birth</th>
                        <th>Role</th>
                        <th>Appointed On</th>
                        <th>PNR</th>
                      </tr>
                    </thead>
                    <tbody>
            `;
            management.forEach(manager => {
                html += `
                      <tr>
                        <td>${escapeHtml(manager.name || 'N/A')}</td>
                        <td>${formatDate(manager.DOB)}</td>
                        <td>${escapeHtml(manager.role || 'N/A')}</td>
                        <td>${formatDate(manager.appointed_on)}</td>
                        <td>${escapeHtml(manager.PNR || 'N/A')}</td>
                      </tr>
                `;
            });
            html += `
                    </tbody>
                  </table>
                </div>
              </div>
            `;
        }

      
        if (history.length > 0) {
            html += `
              <div class="section mb-4">
                <h3 class="mb-3"><i class="fa fa-history"></i> Company History</h3>
                <div class="timeline">
            `;
            history.forEach(event => {
                const eventNum = event.event_number ? ` [${escapeHtml(event.event_number)}]` : '';
                html += `
                  <div class="timeline-item" style="border-left: 2px solid #007bff; padding-left: 20px; margin-bottom: 20px; position: relative;">
                    <div class="timeline-marker" style="position: absolute; left: -6px; top: 5px; width: 10px; height: 10px; background-color: #007bff; border-radius: 50%;"></div>
                    <div class="timeline-content">
                      <h5 style="color: #007bff; margin-bottom: 5px;">${escapeHtml(event.event || 'N/A')}${eventNum}</h5>
                      <p style="margin-bottom: 5px;"><strong>Event Date:</strong> ${escapeHtml(event.event_date || 'N/A')}</p>
                      <p style="margin-bottom: 5px;"><strong>Court:</strong> ${escapeHtml(event.court || 'N/A')}</p>
                      ${event.filed_date ? `<p style="margin-bottom: 5px;"><strong>Filed Date:</strong> ${escapeHtml(event.filed_date)}</p>` : ''}
                    </div>
                  </div>
                `;
            });
            html += `
                </div>
              </div>
            `;
        }

        html += `
            </div>
        `;

        container.innerHTML = html;
    }

   
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

})();

