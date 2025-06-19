document.addEventListener('DOMContentLoaded', () => {
    const userEmailSpan = document.getElementById('userEmail');
    const welcomeMessageDiv = document.getElementById('welcomeMessage');
    const logoutButton = document.getElementById('logoutButton');

    const createFunnelForm = document.getElementById('createFunnelForm');
    const pathIdentifierInput = document.getElementById('pathIdentifier');
    const createFunnelMessageDiv = document.getElementById('createFunnelMessage');

    const funnelLinksTableBody = document.getElementById('funnelLinksTableBody');
    const noFunnelLinksMessage = document.getElementById('noFunnelLinksMessage');
    const referredSignupsCountSpan = document.getElementById('referredSignupsCount');

    // Loader elements
    const funnelLinksLoader = document.getElementById('funnel-links-loader');
    const statsLoader = document.getElementById('stats-loader');

    // Favicon elements
    const faviconUploadInput = document.getElementById('favicon-upload-input');
    const uploadFaviconButton = document.getElementById('upload-favicon-button');
    const faviconStatusMessageDiv = document.getElementById('favicon-status-message');
    const currentFaviconPreviewImg = document.getElementById('current-favicon-preview');
    const noFaviconMessageSpan = document.getElementById('no-favicon-message');


    const API_BASE_URL = 'http://127.0.0.1:5000/api'; // Assuming backend runs here
    const FRONTEND_DOMAIN = 'unhyreable.com'; // For displaying full URLs

    // --- Loader Helper Functions ---
    function showLoader(loaderElement) {
        if (loaderElement) loaderElement.style.display = 'block';
    }

    function hideLoader(loaderElement) {
        if (loaderElement) loaderElement.style.display = 'none';
    }

    // --- General Message Display ---
    function displayMessage(element, message, isError = false) {
        if (element) {
            element.textContent = message;
            element.className = isError ? 'text-red-500 text-sm' : 'text-green-500 text-sm';
            element.classList.add('mt-3');
        }
    }

    // --- Authentication Check ---
    async function checkAuth() {
        try {
            const response = await fetch(`${API_BASE_URL}/check_auth`);
            if (!response.ok) { // Handles network errors or non-200 responses that are not JSON
                if (response.status === 401) { // Specifically for unauthorized
                     window.location.href = 'login.html';
                     return;
                }
                throw new Error(`Auth check failed: ${response.status}`);
            }
            const data = await response.json();

            if (data.is_authenticated) {
                if (userEmailSpan) userEmailSpan.textContent = data.email;
                if (welcomeMessageDiv) welcomeMessageDiv.textContent = `Welcome, ${data.email}!`;

                // Display current favicon if available
                if (data.favicon_url) {
                    if (currentFaviconPreviewImg) {
                        currentFaviconPreviewImg.src = data.favicon_url;
                        currentFaviconPreviewImg.style.display = 'inline-block';
                    }
                    if (noFaviconMessageSpan) noFaviconMessageSpan.style.display = 'none';
                } else {
                    if (currentFaviconPreviewImg) currentFaviconPreviewImg.style.display = 'none';
                    if (noFaviconMessageSpan) noFaviconMessageSpan.style.display = 'inline-block';
                }

                // Load other dashboard data
                loadFunnelLinks();
                loadReferredSignupsCount();
            } else {
                window.location.href = 'login.html';
            }
        } catch (error) {
            console.error('Authentication check error:', error);
            displayMessage(welcomeMessageDiv, 'Error checking authentication. Please try logging in again.', true);
            // Optionally redirect to login after a delay or if error is persistent
            // window.location.href = 'login.html';
        }
    }

    // --- Logout ---
    async function logout() {
        try {
            const response = await fetch(`${API_BASE_URL}/logout`, { method: 'POST' }); // Assuming POST for logout
            // Flask-Login logout usually returns success even if not strictly JSON
            if (response.ok) {
                window.location.href = 'login.html';
            } else {
                const data = await response.json().catch(() => ({})); // Try to parse error, default to empty
                console.error('Logout failed:', data.error || 'Unknown error');
                alert('Logout failed. Please try again.');
            }
        } catch (error) {
            console.error('Logout error:', error);
            alert('An error occurred during logout. Please try again.');
        }
    }
    if (logoutButton) {
        logoutButton.addEventListener('click', logout);
    }

    // --- Create Funnel Link ---
    async function handleCreateFunnel(event) {
        event.preventDefault();
        const pathIdentifier = pathIdentifierInput.value.trim();
        if (!pathIdentifier) {
            displayMessage(createFunnelMessageDiv, 'Path identifier cannot be empty.', true);
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/funnels/create`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path_identifier: pathIdentifier })
            });
            const data = await response.json();
            if (response.ok) {
                displayMessage(createFunnelMessageDiv, `Success! Link created: ${FRONTEND_DOMAIN}/${data.funnel_path}`, false);
                createFunnelForm.reset();
                loadFunnelLinks(); // Refresh the list
            } else {
                displayMessage(createFunnelMessageDiv, data.error || 'Failed to create link.', true);
            }
        } catch (error) {
            console.error('Create funnel error:', error);
            displayMessage(createFunnelMessageDiv, 'An error occurred. Please try again.', true);
        }
    }
    if (createFunnelForm) {
        createFunnelForm.addEventListener('submit', handleCreateFunnel);
    }

    // --- Fetch and Display Funnel Links ---
    async function loadFunnelLinks() {
        showLoader(funnelLinksLoader);
        if (funnelLinksTableBody) funnelLinksTableBody.style.display = 'none'; // Hide table while loading
        if (noFunnelLinksMessage) noFunnelLinksMessage.classList.add('hidden'); // Hide no links message

        try {
            const response = await fetch(`${API_BASE_URL}/funnels/my_links`);
             if (response.status === 401) { // Not logged in
                window.location.href = 'login.html';
                return;
            }
            if (!response.ok) throw new Error(`Failed to fetch links: ${response.status}`);

            const links = await response.json();
            funnelLinksTableBody.innerHTML = ''; // Clear existing rows

            if (links.length === 0) {
                if (noFunnelLinksMessage) noFunnelLinksMessage.classList.remove('hidden');
            } else {
                if (noFunnelLinksMessage) noFunnelLinksMessage.classList.add('hidden');
                links.forEach(link => {
                    const row = funnelLinksTableBody.insertRow();
                    row.innerHTML = `
                        <td class="px-5 py-3 border-b border-gray-200 bg-white text-sm">
                            <a href="http://${link.full_url}" target="_blank" class="text-blue-600 hover:text-blue-800">${link.full_url}</a>
                        </td>
                        <td class="px-5 py-3 border-b border-gray-200 bg-white text-sm">${link.path_identifier}</td>
                        <td class="px-5 py-3 border-b border-gray-200 bg-white text-sm">${link.click_count}</td>
                        <td class="px-5 py-3 border-b border-gray-200 bg-white text-sm">${link.leads_generated_count}</td>
                        <td class="px-5 py-3 border-b border-gray-200 bg-white text-sm">
                            <button class="edit-page-button bg-blue-500 hover:bg-blue-700 text-white font-bold py-1 px-2 rounded text-xs"
                                    data-funnel-link-id="${link.id}"
                                    data-funnel-link-path="${link.path_identifier}">
                                Edit Page
                            </button>
                        </td>
                    `;
                });
            }
        } catch (error) {
            console.error('Error loading funnel links:', error);
            if (funnelLinksTableBody) funnelLinksTableBody.innerHTML = `<tr><td colspan="5" class="text-red-500 p-4">Error loading links.</td></tr>`;
            if (noFunnelLinksMessage) noFunnelLinksMessage.classList.add('hidden'); // Keep hidden on error
        } finally {
            hideLoader(funnelLinksLoader);
            if (funnelLinksTableBody) funnelLinksTableBody.style.display = ''; // Show table again
            // noFunnelLinksMessage visibility is handled inside try block based on data
        }
    }

    // --- Event listener for Edit Page buttons (using event delegation) ---
    if (funnelLinksTableBody) {
        funnelLinksTableBody.addEventListener('click', function(event) {
            if (event.target.classList.contains('edit-page-button')) {
                const button = event.target;
                const funnelLinkId = button.dataset.funnelLinkId;
                if (funnelLinkId) {
                    window.location.href = `/editor.html?funnel_link_id=${funnelLinkId}`;
                } else {
                    console.error('Funnel Link ID not found on button.');
                    alert('Could not find the link ID to edit.');
                }
            }
        });
    }

    // --- Fetch and Display Referred Signups Count ---
    async function loadReferredSignupsCount() {
        showLoader(statsLoader);
        if (referredSignupsCountSpan) referredSignupsCountSpan.style.display = 'none';
        try {
            const response = await fetch(`${API_BASE_URL}/analytics/my_referred_signups_count`);
            if (response.status === 401) { // Not logged in
                window.location.href = 'login.html';
                return;
            }
            if (!response.ok) throw new Error(`Failed to fetch stats: ${response.status}`);

            const data = await response.json();
            if (referredSignupsCountSpan) {
                referredSignupsCountSpan.textContent = data.referred_signups_count;
            }
        } catch (error) {
            console.error('Error loading referred signups count:', error);
            if (referredSignupsCountSpan) {
                referredSignupsCountSpan.textContent = 'Error';
                referredSignupsCountSpan.classList.add('text-red-500');
            }
        } finally {
            hideLoader(statsLoader);
            if (referredSignupsCountSpan) referredSignupsCountSpan.style.display = '';
        }
    }

    // --- Initial Load ---
    checkAuth(); // This will trigger other data loads if authentication is successful

    // --- Favicon Upload ---
    async function handleFaviconUpload() {
        if (!faviconUploadInput || !faviconUploadInput.files || faviconUploadInput.files.length === 0) {
            displayMessage(faviconStatusMessageDiv, 'Please select a file to upload.', true);
            return;
        }
        const file = faviconUploadInput.files[0];
        const formData = new FormData();
        formData.append('file', file);

        // Consider adding a small loader specific to the favicon upload button if desired
        if (uploadFaviconButton) uploadFaviconButton.disabled = true;

        try {
            const response = await fetch(`${API_BASE_URL}/user/favicon`, {
                method: 'POST',
                body: formData,
                // Content-Type is automatically set by browser for FormData
            });
            const data = await response.json(); // Always expect JSON back for messages

            if (response.ok) {
                displayMessage(faviconStatusMessageDiv, data.message || 'Favicon uploaded successfully!', false);
                if (data.favicon_url && currentFaviconPreviewImg) {
                    currentFaviconPreviewImg.src = data.favicon_url + '?t=' + new Date().getTime(); // Cache buster
                    currentFaviconPreviewImg.style.display = 'inline-block';
                }
                if (noFaviconMessageSpan) noFaviconMessageSpan.style.display = 'none';
                faviconUploadInput.value = ''; // Clear the file input
            } else {
                displayMessage(faviconStatusMessageDiv, data.message || 'Failed to upload favicon.', true);
            }
        } catch (error) {
            console.error('Favicon upload error:', error);
            displayMessage(faviconStatusMessageDiv, 'An error occurred during favicon upload.', true);
        } finally {
            if (uploadFaviconButton) uploadFaviconButton.disabled = false;
        }
    }

    if (uploadFaviconButton) {
        uploadFaviconButton.addEventListener('click', handleFaviconUpload);
    }
});
