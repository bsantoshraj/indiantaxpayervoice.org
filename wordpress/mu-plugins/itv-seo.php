<?php
/**
 * Plugin Name: ITV SEO
 * Description: Meta descriptions, Open Graph and Twitter cards, Organization/WebSite structured data, en-IN language, XML sitemaps and the optional cookieless Cloudflare Web Analytics beacon. Kept in-house instead of a general SEO plugin to keep the attack surface small.
 * Version: 0.1.0
 *
 * Indexing itself is decided by the "blog_public" option, which bootstrap.sh sets
 * from ITV_ENV: production is indexable, local and staging are not.
 */

defined( 'ABSPATH' ) || exit;

const ITV_SEO_LOCALE = 'en_IN';

/** The page's own summary (its excerpt, set from bootstrap.sh), else the site tagline. */
function itv_seo_description() {
	if ( is_singular() && ! is_front_page() ) {
		$excerpt = get_post_field( 'post_excerpt', get_queried_object_id() );
		if ( $excerpt ) {
			return wp_strip_all_tags( $excerpt );
		}
	}
	if ( is_front_page() ) {
		$excerpt = get_post_field( 'post_excerpt', (int) get_option( 'page_on_front' ) );
		if ( $excerpt ) {
			return wp_strip_all_tags( $excerpt );
		}
	}
	return get_bloginfo( 'description' );
}

function itv_seo_url() {
	if ( is_front_page() ) {
		return home_url( '/' );
	}
	return is_singular() ? wp_get_canonical_url() : home_url( add_query_arg( array() ) );
}

// Indian English rather than WordPress's default en-US.
add_filter(
	'language_attributes',
	function ( $output ) {
		return preg_replace( '/lang="[^"]*"/', 'lang="en-IN"', $output );
	}
);

// Sitemaps follow blog_public by default (off when indexing is discouraged); keep
// them on everywhere so staging can be checked. Staging stays noindex regardless.
add_filter( 'wp_sitemaps_enabled', '__return_true' );
// No author sitemap: it would publish the admin's username.
add_filter(
	'wp_sitemaps_add_provider',
	function ( $provider, $name ) {
		return 'users' === $name ? false : $provider;
	},
	10,
	2
);

add_action(
	'wp_head',
	function () {
		$description = itv_seo_description();
		$title       = is_front_page() ? get_bloginfo( 'name' ) . ' – ' . get_bloginfo( 'description' ) : wp_get_document_title();
		$image       = get_stylesheet_directory_uri() . '/assets/share.png';
		$tags        = array(
			array( 'name', 'description', $description ),
			array( 'property', 'og:type', 'website' ),
			array( 'property', 'og:site_name', get_bloginfo( 'name' ) ),
			array( 'property', 'og:locale', ITV_SEO_LOCALE ),
			array( 'property', 'og:title', $title ),
			array( 'property', 'og:description', $description ),
			array( 'property', 'og:url', itv_seo_url() ),
			array( 'property', 'og:image', $image ),
			array( 'property', 'og:image:width', '1200' ),
			array( 'property', 'og:image:height', '630' ),
			array( 'property', 'og:image:alt', get_bloginfo( 'name' ) . ': ' . get_bloginfo( 'description' ) ),
			array( 'name', 'twitter:card', 'summary_large_image' ),
			array( 'name', 'twitter:title', $title ),
			array( 'name', 'twitter:description', $description ),
			array( 'name', 'twitter:image', $image ),
		);
		foreach ( $tags as list( $attr, $key, $value ) ) {
			printf( '<meta %s="%s" content="%s">' . "\n", $attr, esc_attr( $key ), esc_attr( $value ) );
		}

		// Structured data: only facts that are true of the initiative today.
		if ( is_front_page() ) {
			$graph = array(
				'@context' => 'https://schema.org',
				'@graph'   => array(
					array(
						'@type'       => 'Organization',
						'@id'         => home_url( '/#organization' ),
						'name'        => get_bloginfo( 'name' ),
						'url'         => home_url( '/' ),
						'logo'        => get_stylesheet_directory_uri() . '/assets/icon-512.png',
						'email'       => 'hello@indiantaxpayervoice.org',
						'description' => $description,
					),
					array(
						'@type'      => 'WebSite',
						'@id'        => home_url( '/#website' ),
						'name'       => get_bloginfo( 'name' ),
						'url'        => home_url( '/' ),
						'inLanguage' => 'en-IN',
						'publisher'  => array( '@id' => home_url( '/#organization' ) ),
					),
				),
			);
			echo '<script type="application/ld+json">' . wp_json_encode( $graph, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE ) . "</script>\n";
		}
	},
	5
);

// Cloudflare Web Analytics: cookieless page-view counts, no personal data stored.
// Only on the website; the survey runs on a separate host and is never tracked.
add_action(
	'wp_footer',
	function () {
		$token = defined( 'ITV_CF_BEACON_TOKEN' ) ? ITV_CF_BEACON_TOKEN : '';
		if ( ! preg_match( '/^[0-9a-f]{32}$/', $token ) || is_user_logged_in() ) {
			return;
		}
		printf(
			'<script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon=\'%s\'></script>' . "\n",
			esc_attr( wp_json_encode( array( 'token' => $token ) ) )
		);
	}
);
