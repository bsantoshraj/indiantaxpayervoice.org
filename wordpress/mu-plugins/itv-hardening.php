<?php
/**
 * Plugin Name: ITV Hardening
 * Description: Stops WordPress revealing account names and its version to visitors. The site has no public authors, so author archives and the users API are not needed.
 * Version: 0.1.0
 */

defined( 'ABSPATH' ) || exit;

// Users API (/wp-json/wp/v2/users) lists account slugs: only for logged-in editors.
add_filter(
	'rest_endpoints',
	function ( $endpoints ) {
		if ( is_user_logged_in() ) {
			return $endpoints;
		}
		foreach ( array_keys( $endpoints ) as $route ) {
			if ( 0 === strpos( $route, '/wp/v2/users' ) ) {
				unset( $endpoints[ $route ] );
			}
		}
		return $endpoints;
	}
);

// Author archives and ?author=N would redirect to /author/<username>/: send them
// home before WordPress's canonical redirect (priority 10) can reveal the name.
add_action(
	'template_redirect',
	function () {
		if ( is_author() || isset( $_GET['author'] ) ) { // phpcs:ignore WordPress.Security.NonceVerification
			wp_safe_redirect( home_url( '/' ), 301 );
			exit;
		}
	},
	1
);

// No author name in oEmbed responses, and no version number anywhere.
add_filter(
	'oembed_response_data',
	function ( $data ) {
		unset( $data['author_name'], $data['author_url'] );
		return $data;
	}
);
remove_action( 'wp_head', 'wp_generator' );
add_filter( 'the_generator', '__return_empty_string' );
