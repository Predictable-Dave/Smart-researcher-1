document.addEventListener('DOMContentLoaded', function() {
    // Global error handler
    window.addEventListener('error', function(event) {
        console.error('Uncaught error:', event.error);
    });

    // CSRF token retrieval with null check
    const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfTokenMeta ? csrfTokenMeta.getAttribute('content') : '';

    // Safe element getter
    function getElementSafely(id) {
        const element = document.getElementById(id);
        if (!element) {
            console.warn(`Element with id '${id}' not found`);
            return null;
        }
        return element;
    }

    // Safe value setter
    function setValueSafely(element, value) {
        if (element && typeof value !== 'undefined' && value !== null) {
            try {
                element.value = value;
            } catch (error) {
                console.error(`Error setting value for element:`, error);
            }
        }
    }

    // Form element handling - only for research config page
    const researchConfigForm = document.querySelector('#smart-research-form');
    if (researchConfigForm) {
        // Initialize form elements with error handling
        const initializeFormElements = () => {
            const configName = getElementSafely('config_name');
            const formAction = getElementSafely('form-action');
            
            if (formAction) {
                setValueSafely(formAction, 'add_config');
            }
            
            return { configName, formAction };
        };

        // Initialize crew description display
        const initializeCrewDescriptions = () => {
            const descriptionElements = document.querySelectorAll('.crew-description');
            descriptionElements.forEach(element => {
                const crewName = element.getAttribute('data-crew');
                if (crewName) {
                    updateCrewDescription(crewName, element);
                }
            });
        };

        // Update crew description
        const updateCrewDescription = (crewName, element) => {
            if (!window.crews || !window.tasks) {
                console.warn('Crews or tasks data not available');
                return;
            }

            const crew = window.crews.find(c => c && c.Crew && c.Crew.name === crewName);
            if (crew && crew.Crew.tasks) {
                const taskDescriptions = crew.Crew.tasks.map(taskName => {
                    const task = window.tasks.find(t => t && t.Task && t.Task.name === taskName);
                    return task ? `<strong>${taskName}:</strong> ${task.Task.description}` : '';
                }).filter(desc => desc);
                
                if (taskDescriptions.length > 0) {
                    element.innerHTML = taskDescriptions.join('<br><br>');
                } else {
                    element.innerHTML = '<em>No tasks assigned to this crew</em>';
                }
            } else {
                element.innerHTML = '<em>No crew information available</em>';
            }
        };

        // Handle form submission
        researchConfigForm.addEventListener('submit', function(e) {
            const formAction = getElementSafely('form-action');
            if (formAction && !formAction.value) {
                formAction.value = 'add_config';
            }
        });

        // Initialize crew select change handlers
        ['prompt_engineer_crew', 'research_crew', 'research_review_crew'].forEach(selectId => {
            const select = document.getElementById(selectId);
            const descElement = document.getElementById(`${selectId}_desc`);
            
            if (select && descElement) {
                select.addEventListener('change', function() {
                    if (this.value) {
                        updateCrewDescription(this.value, descElement);
                    } else {
                        descElement.innerHTML = '<em>Please select a crew</em>';
                    }
                });
            }
        });

        // Initialize edit buttons
        document.querySelectorAll('.edit-config').forEach(button => {
            button.addEventListener('click', function() {
                try {
                    const config = JSON.parse(this.dataset.config);
                    const configName = getElementSafely('config_name');
                    const formAction = getElementSafely('form-action');
                    
                    if (configName) configName.value = config.name;
                    if (formAction) formAction.value = 'edit_config';
                    
                    ['prompt_engineer_crew', 'research_crew', 'research_review_crew'].forEach(field => {
                        const select = document.getElementById(field);
                        const desc = document.getElementById(`${field}_desc`);
                        if (select && config[field]) {
                            select.value = config[field];
                            if (desc) updateCrewDescription(config[field], desc);
                        }
                    });
                } catch (error) {
                    console.error('Error handling edit button click:', error);
                }
            });
        });

        // Initialize the page
        initializeFormElements();
        initializeCrewDescriptions();
    }
});
