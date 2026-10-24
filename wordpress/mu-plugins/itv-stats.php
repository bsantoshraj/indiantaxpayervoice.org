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

/**
 * Tile-grid map: one equal tile per state/UT, placed roughly where it is (north
 * at the top, the north-east to the right, islands offshore). No boundaries are
 * drawn, so no boundary data or Survey of India licensing is involved, and small
 * UTs get a full-size tile. The tiles are a list with a full text description
 * each; [itv_states_table] remains the tabular alternative.
 */
const ITV_TILE_GRID = array(
	'JK' => array( 3, 1 ), 'LA' => array( 4, 1 ),
	'PB' => array( 2, 2 ), 'HP' => array( 3, 2 ), 'UK' => array( 4, 2 ), 'AR' => array( 9, 2 ),
	'CH' => array( 1, 3 ), 'HR' => array( 2, 3 ), 'DL' => array( 3, 3 ), 'UP' => array( 4, 3 ), 'BR' => array( 5, 3 ), 'SK' => array( 6, 3 ), 'AS' => array( 8, 3 ), 'NL' => array( 9, 3 ),
	'RJ' => array( 2, 4 ), 'MP' => array( 3, 4 ), 'CG' => array( 4, 4 ), 'JH' => array( 5, 4 ), 'WB' => array( 6, 4 ), 'ML' => array( 8, 4 ), 'MN' => array( 9, 4 ),
	'GJ' => array( 1, 5 ), 'DH' => array( 2, 5 ), 'MH' => array( 3, 5 ), 'TS' => array( 4, 5 ), 'OD' => array( 5, 5 ), 'TR' => array( 8, 5 ), 'MZ' => array( 9, 5 ),
	'GA' => array( 2, 6 ), 'KA' => array( 3, 6 ), 'AP' => array( 4, 6 ),
	'LD' => array( 1, 7 ), 'KL' => array( 3, 7 ), 'TN' => array( 4, 7 ), 'PY' => array( 5, 7 ), 'AN' => array( 7, 7 ),
);

add_shortcode(
	'itv_state_map',
	function () {
		$doc = itv_stats_fetch( 'states' );
		if ( ! $doc ) {
			return itv_stats_unavailable();
		}
		$rows = array_column( $doc['data']['states'], null, 'code' );
		$max  = 0;
		foreach ( $rows as $row ) {
			if ( 'published' === ( $row['status'] ?? '' ) ) {
				$max = max( $max, (int) $row['count'] );
			}
		}
		$out  = '<figure class="itv-tilemap-figure">';
		$out .= '<figcaption id="itv-tilemap-caption">' . esc_html__( 'Valid responses by respondent-reported state or union territory. Each square is one state or UT, placed roughly where it is; sizes and borders are not geographic.', 'itv' ) . '</figcaption>';
		$out .= '<ul class="itv-tilemap" aria-labelledby="itv-tilemap-caption">';
		foreach ( ITV_TILE_GRID as $code => $pos ) {
			$row    = $rows[ $code ] ?? array( 'name' => $code, 'status' => 'none' );
			$status = $row['status'] ?? 'suppressed';
			if ( 'published' === $status ) {
				$level = $max ? max( 1, (int) ceil( 5 * (int) $row['count'] / $max ) ) : 1;
				$value = number_format_i18n( (int) $row['count'] );
				/* translators: 1: state name, 2: responses, 3: percent of all responses */
				$text  = sprintf( __( '%1$s: %2$s responses, %3$s%% of all responses', 'itv' ), $row['name'], $value, number_format_i18n( (float) $row['percent'] ) );
				$class = 'itv-tile itv-tile--level' . $level;
			} elseif ( 'none' === $status ) {
				$value = '0';
				/* translators: %s: state name */
				$text  = sprintf( __( '%s: no responses', 'itv' ), $row['name'] );
				$class = 'itv-tile itv-tile--none';
			} else {
				$value = '–';
				/* translators: %s: state name */
				$text  = sprintf( __( '%s: not shown (fewer than the minimum group size, or hidden to protect a smaller group)', 'itv' ), $row['name'] );
				$class = 'itv-tile itv-tile--suppressed';
			}
			$out .= sprintf(
				'<li class="%1$s" style="grid-column:%2$d;grid-row:%3$d" tabindex="0" data-tip="%4$s"><span class="itv-tile__code" aria-hidden="true">%5$s</span><span class="itv-tile__value" aria-hidden="true">%6$s</span><span class="itv-sr-only">%4$s</span></li>',
				esc_attr( $class ),
				(int) $pos[0],
				(int) $pos[1],
				esc_attr( $text ),
				esc_html( $code ),
				esc_html( $value )
			);
		}
		$out .= '</ul>';
		$out .= '<ul class="itv-tilemap-legend" aria-label="' . esc_attr__( 'Key', 'itv' ) . '">'
			. '<li><span class="itv-swatch itv-tile--level1"></span><span class="itv-swatch itv-tile--level3"></span><span class="itv-swatch itv-tile--level5"></span> ' . esc_html__( 'Fewer to more responses', 'itv' ) . '</li>'
			. '<li><span class="itv-swatch itv-tile--suppressed"></span> ' . esc_html__( 'Not shown (small group)', 'itv' ) . '</li>'
			. '<li><span class="itv-swatch itv-tile--none"></span> ' . esc_html__( 'No responses', 'itv' ) . '</li>'
			. '</ul></figure>';
		return $out . itv_stats_meta_note( $doc['meta'] );
	}
);
