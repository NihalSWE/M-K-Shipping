document.addEventListener("DOMContentLoaded", function () {
    
    /* ==========================================================================
       1. Robust Dropdown Logic (Using Event Delegation)
       ========================================================================== */
    document.body.addEventListener("click", function (e) {
        // Find if the click happened inside a dropdown toggle
        const toggleBtn = e.target.closest(".nvx-dropdown-toggle");
        
        if (toggleBtn) {
            e.preventDefault();
            
            // Use .closest() to safely find the parent LI regardless of HTML structure
            const parentLi = toggleBtn.closest(".nvx-has-dropdown");
            const subMenu = parentLi.querySelector(".nvx-dropdown-menu");
            const isOpen = parentLi.classList.contains("nvx-open");

            // Optional: Close other open submenus (Accordion effect)
            document.querySelectorAll(".nvx-has-dropdown.nvx-open").forEach(openLi => {
                if (openLi !== parentLi) {
                    openLi.classList.remove("nvx-open");
                    const otherSubMenu = openLi.querySelector(".nvx-dropdown-menu");
                    if (otherSubMenu) otherSubMenu.style.maxHeight = null;
                }
            });

            // Toggle current submenu
            if (isOpen) {
                parentLi.classList.remove("nvx-open");
                subMenu.style.maxHeight = null;
            } else {
                parentLi.classList.add("nvx-open");
                subMenu.style.maxHeight = subMenu.scrollHeight + "px";
            }
        }
    });

    /* ==========================================================================
       2. Bulletproof Active Link Highlighting (Django Friendly)
       ========================================================================== */
    // Get the full URL (with queries) and base URL (without queries)
    const currentFullUrl = window.location.href; 
    const currentBaseUrl = window.location.href.split('?')[0];

    // Grab all links EXCEPT the toggles themselves
    const allLinks = document.querySelectorAll(".nvx-nav-link:not(.nvx-dropdown-toggle), .nvx-dropdown-link");

    allLinks.forEach(link => {
        // link.href gets the resolved absolute URL from the browser
        const linkHref = link.href; 
        
        // Skip empty links or javascript fallbacks
        if (!linkHref || link.getAttribute("href") === "javascript:void(0);") return;

        // Check for an exact match OR a match ignoring query parameters
        if (linkHref === currentFullUrl || linkHref === currentBaseUrl) {
            
            // 1. Highlight the link itself
            link.classList.add("nvx-active");
            
            // 2. If it's inside a dropdown, open the dropdown and highlight the parent
            if (link.classList.contains("nvx-dropdown-link")) {
                const parentDropdownLi = link.closest(".nvx-has-dropdown");
                
                if (parentDropdownLi) {
                    parentDropdownLi.classList.add("nvx-open");
                    const parentMenu = parentDropdownLi.querySelector(".nvx-dropdown-menu");
                    
                    if (parentMenu) {
                        // Use a tiny timeout to ensure the browser has calculated the height 
                        // properly if elements are rendering dynamically
                        setTimeout(() => {
                            parentMenu.style.maxHeight = parentMenu.scrollHeight + "px";
                        }, 10);
                        
                        // Highlight the parent toggle link lightly
                        const parentToggle = parentDropdownLi.querySelector(".nvx-dropdown-toggle");
                        if (parentToggle) parentToggle.classList.add("nvx-active");
                    }
                }
            }
        }
    });

    /* ==========================================================================
       3. Mobile Sidebar Toggle
       ========================================================================== */
    const sidebarContainer = document.getElementById("nvx-sidebar-container");
    const closeMobileBtn = document.getElementById("nvx-close-mobile-btn");
    
    // Replace '.your-mobile-menu-btn' with your actual header button class/ID
    const openMobileBtn = document.querySelector(".your-mobile-menu-btn"); 

    if (openMobileBtn && sidebarContainer) {
        openMobileBtn.addEventListener("click", function () {
            sidebarContainer.classList.add("nvx-mobile-open");
        });
    }

    if (closeMobileBtn && sidebarContainer) {
        closeMobileBtn.addEventListener("click", function () {
            sidebarContainer.classList.remove("nvx-mobile-open");
        });
    }

    /* ==========================================================================
       4. Resize Handler for Dropdown Heights
       ========================================================================== */
    window.addEventListener("resize", () => {
        document.querySelectorAll(".nvx-has-dropdown.nvx-open .nvx-dropdown-menu").forEach(menu => {
            menu.style.maxHeight = menu.scrollHeight + "px";
        });
    });
});