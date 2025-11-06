(function($) {
    "use strict";

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
            $('.sidebar .collapse').collapse('hide');
        }
    }

    $(document).ready(function() {
        console.log('Sidebar toggle initialized');

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
                    // On mobile, ensure sidebar is properly collapsed
                    if (!$('#sidebar-container').hasClass('sidebar-open')) {
                        closeMobileSidebar();
                    }
                }
            }, 250); // Debounce resize event
        });

        // Bootstrap collapse accordion behavior for sidebar dropdowns
        $('#accordionSidebar .collapse').on('show.bs.collapse', function() {
            const $thisCollapse = $(this);
            $('#accordionSidebar .collapse.show').each(function() {
                if ($(this).attr('id') !== $thisCollapse.attr('id')) {
                    $(this).collapse('hide');
                }
            });
        });

        // Prevent dropdown collapse when clicking inside the collapse content
        $('#accordionSidebar .collapse-inner').on('click', function(e) {
            e.stopPropagation();
        });

        // Scroll to top functionality
        $(document).on('click', 'a.scroll-to-top', function(e) {
            e.preventDefault();
            $('html, body').animate({
                scrollTop: 0
            }, 300);
        });

        // Show/hide scroll-to-top button based on scroll position
        $(window).scroll(function() {
            if ($(this).scrollTop() > 100) {
                $('.scroll-to-top').fadeIn();
            } else {
                $('.scroll-to-top').fadeOut();
            }
        });

        // Initialize sidebar state on page load
        initializeSidebarState();

        // Handle ESC key to close mobile sidebar
        $(document).on('keydown', function(e) {
            if (e.key === "Escape" && $('#sidebar-container').hasClass('sidebar-open')) {
                closeMobileSidebar();
            }
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
            const savedState = localStorage.getItem('sidebarCollapsed');
            const sidebar = $("#sidebar-container");
            const icon = $("#sidebarToggle").find('i');
            
            if (savedState === 'true' && !sidebar.hasClass('sidebar-collapsed')) {
                // Apply collapsed state if it was saved
                $("body").addClass("sidebar-toggled");
                $(".sidebar, #sidebar-container").addClass("sidebar-collapsed");
                icon.removeClass('fa-angle-left').addClass('fa-angle-right');
                $('.sidebar .collapse').collapse('hide');
                console.log('Desktop view: sidebar restored as collapsed');
            } else {
                console.log('Desktop view: sidebar initialized as expanded');
            }
        }
    }

    // Save sidebar state to localStorage
    function saveSidebarState(isCollapsed) {
        localStorage.setItem('sidebarCollapsed', isCollapsed);
    }

    // Update the desktop toggle function to save state
    $(document).ready(function() {
        $("#sidebarToggle").off('click').on('click', function(e) {
            e.preventDefault();
            toggleDesktopSidebar();
            
            // Save the new state
            const isCollapsed = $("#sidebar-container").hasClass("sidebar-collapsed");
            saveSidebarState(isCollapsed);
        });
    });

})(jQuery);
