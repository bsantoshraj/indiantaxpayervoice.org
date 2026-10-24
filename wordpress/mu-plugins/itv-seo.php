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

/**
 * [itv_share]: "Share on WhatsApp" as a plain wa.me link (no third-party script,
 * nothing loaded from WhatsApp until tapped). The shared link carries UTM tags so
 * analytics can tell WhatsApp visits apart.
 */
add_shortcode(
	'itv_share',
	function () {
		$url  = add_query_arg(
			array( 'utm_source' => 'whatsapp', 'utm_medium' => 'share', 'utm_campaign' => 'survey' ),
			home_url( '/participate/' )
		);
		$text = sprintf(
			/* translators: %s: link to the survey */
			__( 'Indian taxpayers: what should we get in return for the taxes we pay? Job-loss protection, health costs, public services. A 5-minute anonymous survey, no name, PAN or Aadhaar: %s', 'itv' ),
			$url
		);
		$icon = '<svg aria-hidden="true" focusable="false" width="20" height="20" viewBox="0 0 24 24"><path fill="currentColor" d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2Zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8s-.4-.1-.6.1-.7.8-.8 1-.3.2-.6.1a6.7 6.7 0 0 1-3.3-2.9c-.2-.4.3-.4.7-1.2.1-.2 0-.3 0-.5l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2 5.2 5.2 0 0 0 1.1 2.7 11.8 11.8 0 0 0 4.5 4c1.7.7 2.3.8 3.2.7.5-.1 1.5-.6 1.7-1.2s.2-1.1.2-1.2-.2-.2-.5-.3Z"/></svg>';
		return '<p class="itv-share"><a class="itv-share__whatsapp" href="' . esc_url( 'https://wa.me/?text=' . rawurlencode( $text ) ) . '" target="_blank" rel="noopener noreferrer">'
			. $icon . '<span>' . esc_html__( 'Share on WhatsApp', 'itv' ) . '</span><span class="itv-sr-only"> ' . esc_html__( '(opens WhatsApp)', 'itv' ) . '</span></a></p>';
	}
);

/**
 * IndexNow: serve the verification file /<id>.txt so search engines accept URL
 * submissions from scripts/indexnow.sh (production only). The id is public by
 * design but kept out of the repository; set ITV_INDEXNOW_ID in .env.
 */
add_action(
	'init',
	function () {
		$id = defined( 'ITV_INDEXNOW_ID' ) ? ITV_INDEXNOW_ID : '';
		if ( preg_match( '/^[a-f0-9]{32}$/', $id ) && wp_parse_url( $_SERVER['REQUEST_URI'] ?? '', PHP_URL_PATH ) === '/' . $id . '.txt' ) { // phpcs:ignore WordPress.Security.ValidatedSanitizedInput
			header( 'Content-Type: text/plain; charset=utf-8' );
			header( 'Cache-Control: public, max-age=86400' );
			echo $id; // phpcs:ignore WordPress.Security.EscapeOutput -- validated hex
			exit;
		}
	},
	0
);
