<?php
/**
 * Plugin Name: ITV Public Statistics
 * Description: Renders approved, precomputed survey aggregates. Reads only the public statistics endpoint; WordPress has no access to survey responses.
 * Version: 0.1.0
 *
 * Shortcodes:
 *   [itv_counters]      Headline counters with honest empty/unavailable states.
 *   [itv_states_table]  Accessible state/UT table (also the map's text alternative).
 */

defined( 'ABSPATH' ) || exit;

// Short TTL: the aggregator already refreshes on a schedule, so stacking a long
// WordPress cache on top would delay new counts by up to two refresh cycles.
const ITV_STATS_CACHE_TTL = 60;

function itv_stats_base_url() {
	return defined( 'ITV_STATS_BASE_URL' ) ? rtrim( ITV_STATS_BASE_URL, '/' ) : '';
}

/**
 * Fetch one endpoint server-side, cached in a transient. Returns null when
 * unavailable so callers can say so instead of showing a misleading zero.
 */
function itv_stats_fetch( $endpoint ) {
	if ( ! in_array( $endpoint, array( 'summary', 'states', 'industries', 'breakdowns', 'distributions', 'trends' ), true ) ) {
		return null;
	}
	$base = itv_stats_base_url();
	if ( '' === $base ) {
		return null;
	}
	$key    = 'itv_stats_' . $endpoint;
	$cached = get_transient( $key );
	if ( is_array( $cached ) ) {
		return $cached;
	}
	$response = wp_safe_remote_get( $base . '/' . $endpoint, array( 'timeout' => 3, 'redirection' => 0 ) );
	if ( is_wp_error( $response ) || 200 !== wp_remote_retrieve_response_code( $response ) ) {
		return null;
	}
	$doc = json_decode( wp_remote_retrieve_body( $response ), true );
	if ( ! is_array( $doc ) || ! isset( $doc['meta'], $doc['data'] ) ) {
		return null;
	}
	set_transient( $key, $doc, ITV_STATS_CACHE_TTL );
	return $doc;
}

// The local stats host is on localhost; allow it explicitly for wp_safe_remote_get.
add_filter(
	'http_request_host_is_external',
	function ( $external, $host ) {
		$base = wp_parse_url( itv_stats_base_url(), PHP_URL_HOST );
		return $external || ( $base && $host === $base );
	},
	10,
	2
);

function itv_stats_unavailable() {
	return '<p class="itv-stats-unavailable" role="status">' .
		esc_html__( 'Survey statistics are not available right now. Please check back later.', 'itv' ) .
		'</p>';
}

function itv_stats_meta_note( $meta ) {
	$methodology = home_url( $meta['methodology_url'] ?? '/survey-methodology/' );
	return sprintf(
		'<p class="itv-stats-note"><small>%s %s <a href="%s">%s</a></small></p>',
		esc_html( $meta['representativeness'] ?? '' ),
		esc_html(
			sprintf(
				/* translators: 1: refresh time (UTC), 2: minimum group size, 3: rounding base */
				__( 'Last refreshed %1$s UTC; updated hourly. Groups with fewer than %2$d responses are not shown, and counts are rounded to the nearest %3$d.', 'itv' ),
				str_replace( array( 'T', 'Z' ), array( ' ', '' ), $meta['generated_at'] ?? '' ),
				(int) ( $meta['min_cohort'] ?? 0 ),
				(int) ( $meta['rounding'] ?? 5 )
			)
		),
		esc_url( $methodology ),
		esc_html__( 'How these figures are calculated', 'itv' )
	);
}

add_shortcode(
	'itv_counters',
	function () {
		$doc = itv_stats_fetch( 'summary' );
		if ( ! $doc ) {
			return itv_stats_unavailable();
		}
		$d     = $doc['data'];
		$items = array(
			array( __( 'Valid survey responses', 'itv' ), number_format_i18n( (int) $d['valid_responses'] ) ),
			array(
				__( 'States and union territories represented', 'itv' ),
				sprintf( '%s / %s', number_format_i18n( (int) $d['states_represented'] ), number_format_i18n( (int) $d['states_total'] ) ),
			),
			array( __( 'Industries represented', 'itv' ), number_format_i18n( (int) $d['industries_represented'] ) ),
		);
		$out = '<dl class="itv-counters">';
		foreach ( $items as $item ) {
			$out .= '<div class="itv-counter"><dt>' . esc_html( $item[0] ) . '</dt><dd>' . esc_html( $item[1] ) . '</dd></div>';
		}
		$out .= '</dl>';
		if ( 0 === (int) $d['valid_responses'] ) {
			$out .= '<p role="status">' . esc_html__( 'No valid responses have been recorded yet.', 'itv' ) . '</p>';
		}
		return $out . itv_stats_meta_note( $doc['meta'] );
	}
);

add_shortcode(
	'itv_states_table',
	function () {
		$doc = itv_stats_fetch( 'states' );
		if ( ! $doc ) {
			return itv_stats_unavailable();
		}
		$labels = array(
			'published'  => '',
			'suppressed' => __( 'Not shown (fewer responses than the minimum group size, or hidden to protect a smaller group)', 'itv' ),
			'none'       => __( 'No responses', 'itv' ),
		);
		// Scrollable, focusable region so the table never widens the page on small screens.
		$out  = '<div class="itv-table-wrap" role="region" tabindex="0" aria-label="' . esc_attr__( 'Responses by state or union territory', 'itv' ) . '">';
		$out .= '<table class="itv-table"><caption>' . esc_html__( 'Valid responses by respondent-reported state or union territory', 'itv' ) . '</caption>';
		$out .= '<thead><tr><th scope="col">' . esc_html__( 'State / UT', 'itv' ) . '</th><th scope="col">' . esc_html__( 'Responses', 'itv' ) .
			'</th><th scope="col">' . esc_html__( 'Share', 'itv' ) . '</th></tr></thead><tbody>';
		foreach ( $doc['data']['states'] as $row ) {
			$status = $row['status'] ?? 'suppressed';
			if ( 'published' === $status ) {
				$count = number_format_i18n( (int) $row['count'] );
				$pct   = number_format_i18n( (float) $row['percent'] ) . '%';   // whole numbers (rounded data)
			} else {
				$count = $labels[ $status ] ?? $labels['suppressed'];
				$pct   = '—';
			}
			$out .= '<tr><th scope="row">' . esc_html( $row['name'] ) . '</th><td>' . esc_html( $count ) . '</td><td>' . esc_html( $pct ) . '</td></tr>';
		}
		$out .= '</tbody></table></div>';
		return $out . itv_stats_meta_note( $doc['meta'] );
	}
);
