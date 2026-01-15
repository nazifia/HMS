(function($) {
    "use strict";

    // ============================================
    // DROPDOWN TOGGLE FUNCTIONS
    // ============================================

    // Function to toggle a specific dropdown
    function toggleDropdown(dropdownId) {
        const $collapse = $('#' + dropdownId);
        const $trigger = $collapse.prev('.nav-link');
        
        if ($collapse.hasClass('show')) {
            closeDropdown($collapse, $trigger);
        } else {
            // Close all other dropdowns first (accordion behavior)
            closeAllDropdowns();
            openDropdown($collapse, $trigger);
        }
        return false;
    }

    // Function to open a dropdown
    function openDropdown($collapse, $trigger) {
        $collapse.collapse('show');
        updateDropdownIcon($trigger, true);
        
        // Save state to localStorage
        saveDropdownState($collapse.attr('id'), true);
        
        // Scroll into view if needed
        const sidebar = $('#sidebar-container');
        const collapseTop = $collapse.offset().top;
        const sidebarTop = sidebar.offset().top;
        const scrollPos = collapseTop - sidebarTop - 100;
        
        if (scrollPos < 0) {
            sidebar.animate({ scrollTop: sidebar.scrollTop() + scrollPos }, 300);
        }
    }

    // Function to close a dropdown
    function closeDropdown($collapse, $trigger) {
        $collapse.collapse('hide');
        updateDropdownIcon($trigger, false);
        
        // Save state to localStorage
        saveDropdownState($collapse.attr('id'), false);
    }

    // Function to close all dropdowns
    function closeAllDropdowns() {
        $('.sidebar .collapse.show').each(function() {
            const $collapse = $(this);
            const $trigger = $collapse.prev('.nav-link');
            $collapse.collapse('hide');
            updateDropdownIcon($trigger, false);
            saveDropdownState($collapse.attr('id'), false);
        });
    }

    // Function to update dropdown arrow icon rotation
    function updateDropdownIcon($trigger, isOpen) {
        let $icon = $trigger.find('.rotate-icon');
        
        if ($icon.length === 0) {
            // Look for icon in the nav-link (could be after the span text)
            $icon = $trigger.find('i.fa-chevron-right, i.fa-chevron-down, i.fas.fa-chevron-right, i.fas.fa-chevron-down');
        }
        
        if ($icon.length === 0) {
            // Create rotation icon if not found
            $icon = $('<i class="fas fa-chevron-right rotate-icon ms-auto" style="transition: transform 0.3s ease;"></i>');
            $trigger.append($icon);
        }
        
        // Update icon and rotation
        $icon.removeClass('fa-chevron-right fa-chevron-down fas fa-chevron-right fas fa-chevron-down');
        $icon.addClass(isOpen ? 'fa-chevron-down' : 'fa-chevron-right');
        $icon.css('transform', isOpen ? 'rotate(90deg)' : 'rotate(0deg)');
    }

    // Save dropdown state to localStorage
    function saveDropdownState(dropdownId, isOpen) {
        try {
            const states = JSON.parse(localStorage.getItem('sidebarDropdownStates') || '{}');
            states[dropdownId] = isOpen;
            localStorage.setItem('sidebarDropdownStates', JSON.stringify(states));
        } catch (e) {
            console.warn('Could not save dropdown state:', e);
        }
    }

    // Get saved dropdown states from localStorage
    function getSavedDropdownStates() {
        try {
            return JSON.parse(localStorage.getItem('sidebarDropdownStates') || '{}');
        } catch (e) {
            return {};
        }
    }

    // Restore dropdown states on page load
    function restoreDropdownStates() {
        const states = getSavedDropdownStates();
        
        Object.keys(states).forEach(function(dropdownId) {
            if (states[dropdownId]) {
                const $collapse = $('#' + dropdownId);
                const $trigger = $collapse.prev('.nav-link');
                
                if ($collapse.length && $trigger.length) {
                    // Open the dropdown
                    $collapse.addClass('show');
                    $trigger.addClass('expanded');
                    $trigger.attr('aria-expanded', 'true');
                    updateDropdownIcon($trigger, true);
                }
            }
        });
    }

    // ============================================
    // SIDEBAR TOGGLE FUNCTIONS
    // ============================================

    // Function to toggle mobile sidebar
    function toggleMobileSidebar() {
        const sidebar = $('#sidebar-container');
        const overlay = $('#sidebar-overlay');
        const isOpen = sidebar.hasClass('sidebar-open');
        
        if (isOpen) {
            closeMobileSidebar();
        } else {
            openMobileSidebar();
        }
    }

    // Function to open mobile sidebar
    function openMobileSidebar() {
        const sidebar = $('#sidebar-container');
        const overlay = $('#sidebar-overlay');
        
        sidebar.addClass('sidebar-open');
        overlay.addClass('active');
        $('body').addClass('sidebar-open');
        
        console.log('Mobile sidebar opened');
    }

    // Function to close mobile sidebar
    function closeMobileSidebar() {
        const sidebar = $('#sidebar-container');
        const overlay = $('#sidebar-overlay');
        
        sidebar.removeClass('sidebar-open');
        overlay.removeClass('active');
        $('body').removeClass('sidebar-open');
        
        console.log('Mobile sidebar closed');
    }

    // Function to toggle desktop sidebar collapse state
    function toggleDesktopSidebar() {
        const sidebar = $("#sidebar-container");
        const isCollapsed = sidebar.hasClass("sidebar-collapsed");
        
        // Toggle collapsed state
        $("body").toggleClass("sidebar-toggled");
        $(".sidebar, #sidebar-container").toggleClass("sidebar-collapsed");

        // Update toggle button icon
        const icon = $("#sidebarToggle").find('i');
        if (isCollapsed) {
            icon.removeClass('fa-angle-right').addClass('fa-angle-left');
            console.log('Desktop sidebar expanded');
        } else {
            icon.removeClass('fa-angle-left').addClass('fa-angle-right');
            console.log('Desktop sidebar collapsed');
        }

        // Collapse all dropdown menus when sidebar is collapsed
        if (!isCollapsed) {
            closeAllDropdowns();
        }

        // Save state
        saveSidebarState(!isCollapsed);
    }

    // Save sidebar state to localStorage
    function saveSidebarState(isCollapsed) {
        localStorage.setItem('sidebarCollapsed', isCollapsed);
    }

    // Get sidebar state from localStorage
    function getSidebarState() {
        return localStorage.getItem('sidebarCollapsed') === 'true';
    }

    // ============================================
    // KEYBOARD NAVIGATION
    // ============================================

    function initKeyboardNavigation() {
        const $sidebar = $('#accordionSidebar');
        const $links = $sidebar.find('.nav-link:not([data-bs-toggle="collapse"])');
        const $dropdownLinks = $sidebar.find('.nav-link[data-bs-toggle="collapse"]');
        const $collapseItems = $sidebar.find('.collapse-item');

        // Navigate between nav links
        $links.on('keydown', function(e) {
            const key = e.key;
            
            if (key === 'ArrowDown' || key === 'ArrowUp') {
                e.preventDefault();
                navigateLinks($(this), key === 'ArrowDown' ? 'next' : 'prev', $links);
            }
        });

        // Handle dropdown links
        $dropdownLinks.on('keydown', function(e) {
            const key = e.key;
            
            if (key === 'ArrowRight' || key === 'ArrowDown') {
                e.preventDefault();
                const $collapse = $($(this).attr('href') || $(this).data('bs-target'));
                if (!$collapse.hasClass('show')) {
                    toggleDropdown($collapse.attr('id'));
                }
                // Focus first item in dropdown
                setTimeout(function() {
                    $collapse.find('.collapse-item').first().focus();
                }, 100);
            } else if (key === 'ArrowLeft' || key === 'ArrowUp') {
                e.preventDefault();
                const $collapse = $($(this).attr('href') || $(this).data('bs-target'));
                if ($collapse.hasClass('show')) {
                    toggleDropdown($collapse.attr('id'));
                }
            } else if (key === 'Enter' || key === ' ') {
                e.preventDefault();
                $(this).trigger('click');
            }
        });

        // Handle collapse items
        $collapseItems.on('keydown', function(e) {
            const key = e.key;
            
            if (key === 'ArrowDown' || key === 'ArrowUp') {
                e.preventDefault();
                navigateLinks($(this), key === 'ArrowDown' ? 'next' : 'prev', $collapseItems);
            } else if (key === 'ArrowLeft' || key === 'ArrowUp') {
                e.preventDefault();
                // Go back to parent dropdown link
                const $collapse = $(this).closest('.collapse');
                const $trigger = $collapse.prev('.nav-link');
                $trigger.focus();
            } else if (key === 'Escape') {
                e.preventDefault();
                closeAllDropdowns();
            }
        });
    }

    function navigateLinks($current, direction, $allLinks) {
        const index = $allLinks.index($current);
        let newIndex;
        
        if (direction === 'next') {
            newIndex = index < $allLinks.length - 1 ? index + 1 : 0;
        } else {
            newIndex = index > 0 ? index - 1 : $allLinks.length - 1;
        }
        
        $allLinks.eq(newIndex).focus();
    }

    // ============================================
    // INITIALIZATION
    // ============================================

    $(document).ready(function() {
        console.log('Sidebar toggle initialized');

        // Initialize dropdown icons
        $('.sidebar .nav-link[data-bs-toggle="collapse"]').each(function() {
            updateDropdownIcon($(this), $(this).next('.collapse').hasClass('show'));
        });

        // Desktop sidebar toggle (circular button at bottom of sidebar)
        $("#sidebarToggle").on('click', function(e) {
            e.preventDefault();
            toggleDesktopSidebar();
        });

        // Mobile sidebar toggle (hamburger button in topbar)
        $("#sidebarToggleTop").on('click', function(e) {
            e.preventDefault();
            toggleMobileSidebar();
        });

        // Close mobile sidebar when overlay is clicked
        $('#sidebar-overlay').on('click', function() {
            closeMobileSidebar();
        });

        // Close mobile sidebar when close button is clicked
        $('#mobileSidebarClose').on('click', function() {
            closeMobileSidebar();
        });

        // Bootstrap collapse accordion behavior
        $('.sidebar .collapse').on('show.bs.collapse', function() {
            const $thisCollapse = $(this);
            const $trigger = $thisCollapse.prev('.nav-link');
            
            // Close all other dropdowns first (accordion behavior)
            $('.sidebar .collapse.show').each(function() {
                if ($(this).attr('id') !== $thisCollapse.attr('id')) {
                    const $otherTrigger = $(this).prev('.nav-link');
                    $(this).collapse('hide');
                    updateDropdownIcon($otherTrigger, false);
                    saveDropdownState($(this).attr('id'), false);
                }
            });
            
            // Update current dropdown icon
            updateDropdownIcon($trigger, true);
            saveDropdownState($thisCollapse.attr('id'), true);
        });

        $('.sidebar .collapse').on('hide.bs.collapse', function() {
            const $thisCollapse = $(this);
            const $trigger = $thisCollapse.prev('.nav-link');
            updateDropdownIcon($trigger, false);
            saveDropdownState($thisCollapse.attr('id'), false);
        });

        $('.sidebar .collapse').on('shown.bs.collapse', function() {
            // Scroll dropdown into view if needed
            const $collapse = $(this);
            const sidebar = $('#sidebar-container');
            const collapseTop = $collapse.offset().top;
            const sidebarTop = sidebar.offset().top;
            const sidebarScrollTop = sidebar.scrollTop();
            
            if (collapseTop < sidebarTop) {
                sidebar.animate({
                    scrollTop: sidebarScrollTop + (collapseTop - sidebarTop) - 50
                }, 200);
            }
        });

        // Prevent dropdown collapse when clicking inside the collapse content
        $('.sidebar .collapse-inner').on('click', function(e) {
            e.stopPropagation();
        });

        // Handle window resize events
        let resizeTimer;
        $(window).on('resize', function() {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(function() {
                const windowWidth = $(window).width();
                
                if (windowWidth >= 768) {
                    // If we're on desktop, remove mobile sidebar classes
                    if ($('#sidebar-container').hasClass('sidebar-open')) {
                        closeMobileSidebar();
                    }
                } else {
                    // On mobile, ensure sidebar is properly closed
                    closeMobileSidebar();
                }
            }, 250); // Debounce resize event
        });

        // Initialize sidebar state
        initializeSidebarState();

        // Restore dropdown states
        restoreDropdownStates();

        // Initialize keyboard navigation
        initKeyboardNavigation();

        // Handle ESC key to close mobile sidebar
        $(document).on('keydown', function(e) {
            if (e.key === "Escape" && $('#sidebar-container').hasClass('sidebar-open')) {
                closeMobileSidebar();
            }
            // ESC also closes dropdowns when in sidebar
            if (e.key === "Escape" && $('.sidebar .collapse.show').length > 0) {
                closeAllDropdowns();
            }
        });

        // Double-click on nav-link to toggle dropdown (for desktop accessibility)
        $('.sidebar .nav-link[data-bs-toggle="collapse"]').on('dblclick', function(e) {
            e.preventDefault();
            const $collapse = $($(this).attr('href') || $(this).data('bs-target'));
            toggleDropdown($collapse.attr('id'));
        });
    });

    // Initialize sidebar state based on screen size
    function initializeSidebarState() {
        const windowWidth = $(window).width();
        
        if (windowWidth < 768) {
            // Mobile: ensure sidebar starts closed
            closeMobileSidebar();
            console.log('Mobile view: sidebar initialized as closed');
        } else {
            // Desktop: check for saved sidebar state
            const sidebar = $("#sidebar-container");
            const icon = $("#sidebarToggle").find('i');
            
            if (getSidebarState() && !sidebar.hasClass('sidebar-collapsed')) {
                // Apply collapsed state if it was saved
                $("body").addClass("sidebar-toggled");
                $(".sidebar, #sidebar-container").addClass("sidebar-collapsed");
                icon.removeClass('fa-angle-left').addClass('fa-angle-right');
                console.log('Desktop view: sidebar restored as collapsed');
            } else {
                console.log('Desktop view: sidebar initialized as expanded');
            }
        }
    }

    // ============================================
    // EXPOSE FUNCTIONS GLOBALLY
    // ============================================

    // Make functions available globally for programmatic control
    window.SidebarUtils = {
        toggleDropdown: toggleDropdown,
        openDropdown: function(dropdownId) {
            const $collapse = $('#' + dropdownId);
            const $trigger = $collapse.prev('.nav-link');
            openDropdown($collapse, $trigger);
        },
        closeDropdown: function(dropdownId) {
            const $collapse = $('#' + dropdownId);
            const $trigger = $collapse.prev('.nav-link');
            closeDropdown($collapse, $trigger);
        },
        closeAllDropdowns: closeAllDropdowns,
        toggleMobileSidebar: toggleMobileSidebar,
        openMobileSidebar: openMobileSidebar,
        closeMobileSidebar: closeMobileSidebar,
        toggleDesktopSidebar: toggleDesktopSidebar,
        saveSidebarState: saveSidebarState
    };

})(jQuery);
