document.addEventListener('DOMContentLoaded', () => {
    const funnelLinkSelector = document.getElementById('funnel-link-selector');
    const editingFunnelLinkPathSpan = document.querySelector('#editing-funnel-link-path span');
    const cssEditor = document.getElementById('css-editor');
    // const htmlEditor = document.getElementById('html-editor'); // GrapesJS will replace this
    const saveButton = document.getElementById('save-button');
    const statusMessageDiv = document.getElementById('status-message');

    const assetUploadInput = document.getElementById('asset-upload-input');
    const uploadAssetButton = document.getElementById('upload-asset-button');
    const assetListUl = document.getElementById('asset-list');
    const assetStatusMessageDiv = document.getElementById('asset-status-message');

    // Loader elements
    const linkSelectorLoader = document.getElementById('link-selector-loader');
    const pageContentLoader = document.getElementById('page-content-loader');
    const saveButtonLoader = document.getElementById('save-button-loader');
    const assetUploadLoader = document.getElementById('asset-upload-loader');
    const assetListLoader = document.getElementById('asset-list-loader');

    let currentSelectedFunnelLinkId = null;

    // --- Loader Helper Functions ---
    function showLoader(loaderElement) {
        if (loaderElement) loaderElement.style.display = 'block';
    }

    function hideLoader(loaderElement) {
        if (loaderElement) loaderElement.style.display = 'none';
    }

    // --- Helper for API calls ---
    async function fetchApi(url, options = {}) {
        options.credentials = 'include'; // Include cookies for authenticated requests
        if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
            options.headers = { ...options.headers, 'Content-Type': 'application/json' };
            options.body = JSON.stringify(options.body);
        }

        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ message: response.statusText }));
                throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
            }
            // For 204 No Content or other non-JSON success responses
            const contentType = response.headers.get("content-type");
            if (contentType && contentType.indexOf("application/json") !== -1) {
                return await response.json();
            } else {
                return { message: "Operation successful", status: response.status }; // Or just return response for further handling
            }
        } catch (error) {
            console.error('API Fetch Error:', error);
            throw error;
        }
    }

    function showStatusMessage(element, message, isError = false) {
        element.textContent = message;
        element.className = `alert ${isError ? 'alert-danger' : 'alert-success'}`;
        element.style.display = 'block';
        setTimeout(() => { element.style.display = 'none'; }, 5000);
    }

    // --- Initialization ---
    async function initializeAppLogic() { // Renamed to avoid confusion with GrapesJS init
        showLoader(linkSelectorLoader);
        try {
            const links = await fetchApi('/api/funnels/my_links');
            funnelLinkSelector.innerHTML = '<option value="">-- Select a Link --</option>'; // Reset
            links.forEach(link => {
                const option = document.createElement('option');
                option.value = link.id; // Store FunnelLink.id
                option.textContent = link.path_identifier; // Display path_identifier
                option.dataset.path = link.path_identifier; // Store path for display
                funnelLinkSelector.appendChild(option);
            });

            // Check for funnel_link_id in URL query parameters
            const urlParams = new URLSearchParams(window.location.search);
            const funnelIdFromUrl = urlParams.get('funnel_link_id');

            if (funnelIdFromUrl) {
                const numericFunnelId = parseInt(funnelIdFromUrl);
                if (!isNaN(numericFunnelId)) {
                    const optionExists = Array.from(funnelLinkSelector.options).some(opt => opt.value == numericFunnelId);
                    if (optionExists) {
                        funnelLinkSelector.value = numericFunnelId;
                    } else {
                        console.warn(`Funnel ID ${numericFunnelId} from URL not found in user's links.`);
                        showStatusMessage(statusMessageDiv, `Funnel ID ${numericFunnelId} from URL not found or not accessible.`, true);
                    }
                }
            }

            handleFunnelLinkChange();
        } catch (error) {
            showStatusMessage(statusMessageDiv, `Error loading funnel links: ${error.message}`, true);
        } finally {
            hideLoader(linkSelectorLoader);
        }
    }

    // --- GrapesJS Initialization ---
    // Store editor instance globally or in a way it can be accessed by other functions
    window.grapesEditor = grapesjs.init({
        container: '#gjs',
        height: '100%', // Or a fixed height like '700px'
        width: 'auto',
        storageManager: false, // Disable built-in GrapesJS storage
        // Example plugins (optional for this step, ensure they don't break if not fully configured)
        // plugins: ['gjs-blocks-basic'],
        // pluginsOpts: {
        //   'gjs-blocks-basic': { flexGrid: true }
        // }
        // Add more configurations as needed in subsequent steps
    });

    // --- GrapesJS Block Definitions & Asset Manager Customization ---
    if (window.grapesEditor) {
        const editor = window.grapesEditor;
        const blockManager = editor.BlockManager;

        // Paragraph Block
        blockManager.add('paragraph', {
            label: 'Paragraph',
            category: 'Basic',
            content: {
                type: 'text',
                content: 'Insert your text here',
                style: { padding: '10px' },
                activeOnRender: true,
            },
        });

        // Header Block
        blockManager.add('header', {
            label: 'Header',
            category: 'Basic',
            content: {
                type: 'text',
                tagName: 'h2',
                content: 'Your Header Text',
                style: { padding: '10px' },
                activeOnRender: true,
            },
        });

        // Custom Image Block
        blockManager.add('custom-image', {
            label: 'Image',
            category: 'Basic',
            activate: true,
            select: true,
            content: {
                type: 'image', // GrapesJS built-in 'image' component
                style: { color: 'black', width: '100px', height: '100px' }, // Default style
                activeOnRender: true,
            },
        });

        // Asset Manager Customization
        const assetManager = editor.AssetManager;
        assetManager.getConfig().upload = false;
        assetManager.getConfig().embedAsBase64 = false;
        assetManager.getConfig().dropzone = false;

        editor.on('asset:open', () => {
            const assetsForGrapes = (window.userAssets || []).map(asset => ({
                src: `/user_uploads/${asset.file_path}`, // IMPORTANT: This path needs to be servable by the backend
                name: asset.file_name,
                type: asset.content_type && asset.content_type.startsWith('image/') ? 'image' : 'file',
                // GrapesJS uses 'type' to filter. 'image' is a common one.
            }));
            assetManager.load(assetsForGrapes); // Use load instead of clear + add for better behavior
        });

        // Close GrapesJS asset manager when an asset is chosen or if the user clicks outside
        editor.on('asset:select', () => {
            // GrapesJS will automatically use the selected asset.
            // No need to call assetManager.close() explicitly if default behavior is fine.
        });
        editor.on('asset:close', () => {
            // This event is triggered when the Asset Manager is closed.
        });


        // Basic Trait for Text Components (Paragraph, Header)
        const defaultTextType = editor.DomComponents.getType('text');
        editor.DomComponents.addType('text', {
            model: {
                defaults: {
                    ...defaultTextType.model.prototype.defaults,
                    traits: [
                        ...(defaultTextType.model.prototype.defaults.traits || []),
                        {
                            type: 'select',
                            label: 'Align',
                            name: 'align', // This will map to style: text-align if not handled by a specific component logic
                            options: [
                                { value: 'left', name: 'Left' },
                                { value: 'center', name: 'Center' },
                                { value: 'right', name: 'Right' },
                                { value: 'justify', name: 'Justify' },
                            ],
                            changeProp: 1, // Trigger change on property update
                        },
                        // Example: Font Size trait (more complex as it needs units, etc.)
                        // { type: 'number', label: 'Font Size (px)', name: 'font-size', units: ['px', 'em', 'rem', '%'], default: '16px', min: 10, step: 1 }
                    ]
                },
                // Ensure the 'align' trait maps to the 'text-align' style
                // This might already be handled by GrapesJS for the 'text' component,
                // but explicitly defining it or listening to trait changes can be done if needed.
                // For simple style mapping, GrapesJS often infers from 'name'.
                // If direct style mapping is needed from a trait:
                // updated(property, value, previous) {
                //   if (property === 'align' && value) {
                //     this.addStyle({'text-align': value});
                //   }
                // }
            },
            view: defaultTextType.view // Extend the default view
        });
    }

    // --- Load Page Content (will be adapted for GrapesJS later) ---
    async function loadPageContent(funnelLinkId) {
        const editor = window.grapesEditor;
        cssEditor.value = ''; // Clear external CSS editor
        if (editor) {
            editor.setComponents(''); // Clear GrapesJS canvas components
            editor.CssComposer.clear(); // Clear GrapesJS canvas styles
        }

        if (!funnelLinkId) {
            editingFunnelLinkPathSpan.textContent = 'N/A';
            currentSelectedFunnelLinkId = null;
            return;
        }
        currentSelectedFunnelLinkId = funnelLinkId;
        const selectedOption = funnelLinkSelector.options[funnelLinkSelector.selectedIndex];
        editingFunnelLinkPathSpan.textContent = selectedOption.dataset.path || 'N/A';

        showLoader(pageContentLoader);
        try {
            const data = await fetchApi(`/api/userpage/content/load?funnel_link_id=${funnelLinkId}`);

            // Load CSS into the dedicated CSS editor textarea
            cssEditor.value = data.css_content || '';

            // Load GrapesJS components (page_data)
            if (data.page_data && Array.isArray(data.page_data)) {
                editor.setComponents(data.page_data);
            } else {
                editor.setComponents(''); // Set to empty if no valid data
            }
            // Note: GrapesJS also has its own internal CSS (StyleManager).
            // The css_content from our cssEditor is for global page styles not directly tied to components by GrapesJS.
            // If we want GrapesJS to manage all CSS, we'd load data.css_content into editor.CssComposer.addCollection()
            // For now, keeping cssEditor separate and GrapesJS components having their own styles is fine.
            // If GrapesJS project data was saved (which includes its own CSS), then:
            // editor.loadProjectData(data.page_data); // If page_data was a full GrapesJS project

        } catch (error) {
            showStatusMessage(statusMessageDiv, `Error loading page content: ${error.message}`, true);
        } finally {
            hideLoader(pageContentLoader);
        }
    }

    // --- Save Page Content ---
    async function savePageContent() {
        if (!currentSelectedFunnelLinkId) {
            showStatusMessage(statusMessageDiv, 'Please select a funnel link first.', true);
            return;
        }
        const editor = window.grapesEditor;
        let pageDataToSave = [];
        if (editor) {
            // Get GrapesJS components as an array of objects
            // GrapesJS toJSON() method on components/collection can be used.
            // We need to ensure the output matches what our backend block renderer expects.
            // For now, we assume editor.getComponents().toJSON() provides a compatible structure
            // or a structure that GrapesJS can reload via editor.setComponents().
            // The backend's block renderer expects a list of objects like:
            // { type: 'paragraph', text: 'Hello' }
            // { type: 'header', text: 'Title', level: 1 }
            // { type: 'image', src: '/path', alt: 'img' }
            // GrapesJS components toJSON() might be more complex.
            // A simple mapping might be needed if default toJSON() isn't suitable.
            // For now, let's save the direct GrapesJS component structure.
            pageDataToSave = editor.getComponents().toJSON();
            if (!Array.isArray(pageDataToSave)) { // Ensure it's an array
                pageDataToSave = [];
            }
        }

        // Get CSS from the dedicated CSS editor textarea
        const cssContentToSave = cssEditor.value;
        // If also getting CSS from GrapesJS Style Manager:
        // const grapesCss = editor.getCss({ avoidProtected: true });
        // Then potentially merge or decide which one is authoritative. For now, only use cssEditor.

        showLoader(saveButtonLoader);
        saveButton.disabled = true;
        try {
            await fetchApi('/api/userpage/content/save', {
                method: 'POST',
                body: {
                    funnel_link_id: parseInt(currentSelectedFunnelLinkId),
                    page_data: page_data_to_save, // Will be GrapesJS JSON data
                    css_content: cssContent
                }
            });
            showStatusMessage(statusMessageDiv, 'Content saved successfully!', false);
        } catch (error) {
            showStatusMessage(statusMessageDiv, `Error saving content: ${error.message}`, true);
        } finally {
            hideLoader(saveButtonLoader);
            saveButton.disabled = false;
        }
    }

    // --- Asset Management ---
    window.userAssets = []; // Initialize global store for assets

    async function loadUserAssets() {
        assetListUl.innerHTML = '';
        showLoader(assetListLoader);
        try {
            const assetsData = await fetchApi('/api/userpage/assets');
            window.userAssets = assetsData; // Store for GrapesJS Asset Manager

            if (assetsData.length === 0) {
                assetListUl.innerHTML = '<li>No assets uploaded yet.</li>';
            } else {
                assetsData.forEach(asset => {
                    const li = document.createElement('li');
                    // Use the same path construction as for GrapesJS asset manager for consistency
                    const assetUrl = `/user_uploads/${asset.file_path}`;
                    li.innerHTML = `
                        <div class="d-flex justify-content-between align-items-center">
                            <span>
                                <strong>${asset.file_name}</strong> (Type: ${asset.content_type})<br>
                                Path: <code>${assetUrl}</code>
                            </span>
                            <span>
                                <button class="btn btn-sm btn-outline-secondary copy-path-btn mr-1" data-path="${assetUrl}">Copy</button>
                                <button class="btn btn-sm btn-outline-danger delete-asset-btn" data-asset-id="${asset.id}">Delete</button>
                            </span>
                        </div>
                    `;
                    assetListUl.appendChild(li);
                });
            }
        } catch (error) {
            showStatusMessage(assetStatusMessageDiv, `Error loading assets: ${error.message}`, true);
            window.userAssets = []; // Clear on error
        } finally {
            hideLoader(assetListLoader);
            // If GrapesJS asset manager is open, refresh it
            if (window.grapesEditor && window.grapesEditor.AssetManager.isOpen()) {
                 window.grapesEditor.trigger('asset:open'); // Re-trigger to reload with new assets
            }
        }
    }

    async function uploadAsset() {
        const file = assetUploadInput.files[0];
        if (!file) {
            showStatusMessage(assetStatusMessageDiv, 'Please select a file to upload.', true);
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        showLoader(assetUploadLoader);
        uploadAssetButton.disabled = true;
        assetUploadInput.disabled = true;
        try {
            const result = await fetchApi('/api/userpage/assets/upload', {
                method: 'POST',
                body: formData // FormData sets Content-Type to multipart/form-data automatically
            });
            showStatusMessage(assetStatusMessageDiv, `Asset uploaded: ${result.file_name}`, false);
            assetUploadInput.value = ''; // Clear the file input
            loadUserAssets(); // Refresh asset list
        } catch (error) {
            showStatusMessage(assetStatusMessageDiv, `Error uploading asset: ${error.message}`, true);
        } finally {
            hideLoader(assetUploadLoader);
            uploadAssetButton.disabled = false;
            assetUploadInput.disabled = false;
        }
    }

    async function deleteAsset(assetId) {
        // Consider showing a loader on the specific item or a general one like assetListLoader
        if (!confirm(`Are you sure you want to delete asset ID ${assetId}? This cannot be undone.`)) {
            return;
        }
        showLoader(assetListLoader); // Use general list loader for delete operations
        try {
            await fetchApi(`/api/userpage/assets/${assetId}`, { method: 'DELETE' });
            showStatusMessage(assetStatusMessageDiv, `Asset ${assetId} deleted successfully.`, false);
            loadUserAssets(); // Refresh the list (loader will be hidden by loadUserAssets' finally)
        } catch (error) {
            showStatusMessage(assetStatusMessageDiv, `Error deleting asset ${assetId}: ${error.message}`, true);
            hideLoader(assetListLoader); // Ensure loader is hidden on error if loadUserAssets isn't called or also errors
        }
    }


    // --- Event Listeners ---
    funnelLinkSelector.addEventListener('change', handleFunnelLinkChange);

    function handleFunnelLinkChange() {
        const selectedId = funnelLinkSelector.value;
        loadPageContent(selectedId ? parseInt(selectedId) : null);
        if (selectedId) { // Only load assets if a funnel is selected, though assets are user-wide
            loadUserAssets();
        } else {
            assetListUl.innerHTML = '<li>Select a funnel link to manage its content and see related assets.</li>';
        }
    }

    saveButton.addEventListener('click', savePageContent);
    uploadAssetButton.addEventListener('click', uploadAsset);

    assetListUl.addEventListener('click', function(event) {
        if (event.target.classList.contains('copy-path-btn')) {
            const path = event.target.dataset.path;
            navigator.clipboard.writeText(path).then(() => {
                showStatusMessage(assetStatusMessageDiv, 'Asset path copied to clipboard!', false);
            }).catch(err => {
                showStatusMessage(assetStatusMessageDiv, 'Failed to copy path.', true);
                console.error('Error copying path: ', err);
            });
        }
        if (event.target.classList.contains('delete-asset-btn')) {
            const assetId = event.target.dataset.assetId;
            deleteAsset(assetId);
        }
    });

    // --- Initial Load ---
    initializeAppLogic(); // Initialize app logic (funnel selector, etc.)
    // GrapesJS is initialized above, outside this async function, as it's synchronous.
});
