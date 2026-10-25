<?php
/**
 * Plugin Name: ITV Publish Relay
 * Description: On staging, publishing an article asks GitHub Actions to publish it on production ("Publish article" workflow, which waits for the owner's approval). Does nothing elsewhere.
 * Version: 0.1.0
 */

defined( 'ABSPATH' ) || exit;

// Staging only, and only with a token that may start workflows (a fine-grained
// token for this repository with "Actions: read and write" and nothing else).
if ( 'staging' !== ( defined( 'ITV_ENV' ) ? ITV_ENV : '' ) || ! defined( 'ITV_PUBLISH_DISPATCH_TOKEN' ) || '' === ITV_PUBLISH_DISPATCH_TOKEN ) {
	return;
}

const ITV_PUBLISH_WORKFLOW = 'https://api.github.com/repos/bsantoshraj/indiantaxpayervoice.org/actions/workflows/publish-article.yml/dispatches';

add_action(
	'transition_post_status',
	function ( $new_status, $old_status, $post ) {
		if ( 'publish' !== $new_status || 'publish' === $old_status || 'post' !== $post->post_type ) {
			return;
		}
		$response = wp_remote_post(
			ITV_PUBLISH_WORKFLOW,
			array(
				'timeout' => 15,
				'headers' => array(
					'Accept'               => 'application/vnd.github+json',
					'Authorization'        => 'Bearer ' . ITV_PUBLISH_DISPATCH_TOKEN,
					'X-GitHub-Api-Version' => '2022-11-28',
					'Content-Type'         => 'application/json',
				),
				'body'    => wp_json_encode(
					array(
						'ref'    => 'main',
						'inputs' => array( 'slug' => $post->post_name ),
					)
				),
			)
		);
		$code = is_wp_error( $response ) ? 0 : wp_remote_retrieve_response_code( $response );
		$note = 204 === $code
			? sprintf( 'Production publish requested for "%s". Approve it in GitHub: Actions > Publish article.', $post->post_title )
			: sprintf( 'Could not request the production publish for "%s" (GitHub answered %s). Run Actions > Publish article by hand with slug %s.', $post->post_title, $code ? $code : 'nothing', $post->post_name );
		set_transient( 'itv_publish_relay_' . get_current_user_id(), array( 204 === $code, $note ), 10 * MINUTE_IN_SECONDS );
		update_post_meta( $post->ID, '_itv_production_publish', gmdate( 'c' ) . ' ' . ( 204 === $code ? 'requested' : "failed ($code)" ) );
	},
	10,
	3
);

// Show the outcome to the editor on the next admin page (the block editor saves in
// the background, so the notice appears after the next page load).
add_action(
	'admin_notices',
	function () {
		$key    = 'itv_publish_relay_' . get_current_user_id();
		$notice = get_transient( $key );
		if ( ! $notice ) {
			return;
		}
		delete_transient( $key );
		printf(
			'<div class="notice notice-%s is-dismissible"><p>%s</p></div>',
			$notice[0] ? 'success' : 'error',
			esc_html( $notice[1] )
		);
	}
);
