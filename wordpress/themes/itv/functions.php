<?php
/**
 * Indian Taxpayer Voice child theme.
 */

defined( 'ABSPATH' ) || exit;

add_action(
	'wp_enqueue_scripts',
	function () {
		// File mtime as version so browsers pick up stylesheet edits immediately.
		wp_enqueue_style( 'itv', get_stylesheet_uri(), array(), (string) filemtime( get_stylesheet_directory() . '/style.css' ) );
	}
);

add_action(
	'wp_head',
	function () {
		printf( '<link rel="icon" type="image/svg+xml" href="%s">' . "\n", esc_url( get_stylesheet_directory_uri() . '/assets/logo-mark.svg' ) );
	}
);
