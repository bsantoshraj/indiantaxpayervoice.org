<?php
/**
 * Plugin Name: ITV Publish Relay
 * Description: On staging, adds "Publish to production" and "Unpublish from production" to each article (Posts list and a Production box in the editor). Each asks GitHub Actions to run "Publish or unpublish article", which waits for the owner's approval. Does nothing elsewhere.
 * Version: 0.3.0
 */

defined( 'ABSPATH' ) || exit;

if ( 'staging' !== ( defined( 'ITV_ENV' ) ? ITV_ENV : '' ) ) {
	return;
}

const ITV_PRODUCTION_WORKFLOW = 'https://api.github.com/repos/bsantoshraj/indiantaxpayervoice.org/actions/workflows/publish-article.yml';

function itv_production_link( $what, $post_id ) {
	return wp_nonce_url(
		admin_url( 'admin-post.php?action=itv_production&do=' . $what . '&post=' . $post_id ),
		'itv_production_' . $what . '_' . $post_id
	);
}

// Links on each article in Posts. Publishing to production is offered only for
// articles published here (reviewed); the workflow checks the text matches too.
add_filter(
	'post_row_actions',
	function ( $actions, $post ) {
		if ( 'post' !== $post->post_type || ! current_user_can( 'publish_posts' ) ) {
			return $actions;
		}
		$link = function ( $what ) use ( $post ) {
			return itv_production_link( $what, $post->ID );
		};
		if ( 'publish' === $post->post_status ) {
			$actions['itv_prod_publish'] = sprintf(
				'<a href="%s" onclick="return confirm(%s)">Publish to production</a>',
				esc_url( $link( 'publish' ) ),
				esc_attr( wp_json_encode( 'Ask GitHub to publish this article on production? You will approve it there.' ) )
			);
		} else {
			$actions['itv_prod_publish'] = '<span style="color:#646970">Publish to production: publish it here first</span>';
		}
		$actions['itv_prod_unpublish'] = sprintf(
			'<a href="%s" onclick="return confirm(%s)" style="color:#b32d2e">Unpublish from production</a>',
			esc_url( $link( 'unpublish' ) ),
			esc_attr( wp_json_encode( 'Ask GitHub to take this article off production? You will approve it there.' ) )
		);
		return $actions;
	},
	10,
	2
);

add_action(
	'admin_post_itv_production',
	function () {
		$what    = isset( $_GET['do'] ) ? sanitize_key( $_GET['do'] ) : '';
		$post_id = isset( $_GET['post'] ) ? absint( $_GET['post'] ) : 0;
		check_admin_referer( 'itv_production_' . $what . '_' . $post_id );
		$post = get_post( $post_id );
		if ( ! current_user_can( 'publish_posts' ) || ! $post || 'post' !== $post->post_type || ! in_array( $what, array( 'publish', 'unpublish' ), true ) ) {
			wp_die( 'Not allowed.' );
		}

		$manual = sprintf( 'Run it by hand: GitHub > Actions > Publish or unpublish article > Run workflow (action %s, slug %s).', $what, $post->post_name );
		if ( 'publish' === $what && 'publish' !== $post->post_status ) {
			$notice = array( false, 'Publish the article here on staging and review it first.' );
		} elseif ( ! defined( 'ITV_PUBLISH_DISPATCH_TOKEN' ) || '' === ITV_PUBLISH_DISPATCH_TOKEN ) {
			$notice = array( false, 'ITV_PUBLISH_DISPATCH_TOKEN is not set on staging, so this cannot start GitHub Actions. ' . $manual );
		} else {
			$response = wp_remote_post(
				ITV_PRODUCTION_WORKFLOW . '/dispatches',
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
							'inputs' => array(
								'action' => $what,
								'slug'   => $post->post_name,
							),
						)
					),
				)
			);
			$code   = is_wp_error( $response ) ? 0 : wp_remote_retrieve_response_code( $response );
			$verb   = 'publish' === $what ? 'Publish' : 'Unpublish';
			$notice = 204 === $code
				? array( true, sprintf( '%s requested for: %s. Approve it in GitHub: Actions > Publish or unpublish article.', $verb, $post->post_title ) )
				: array( false, sprintf( 'GitHub did not accept the request (answered %s). %s', $code ? $code : 'nothing', $manual ) );
			update_post_meta( $post->ID, '_itv_production_request', gmdate( 'c' ) . " $what " . ( 204 === $code ? 'requested' : "failed ($code)" ) );
		}
		set_transient( 'itv_production_notice_' . get_current_user_id(), $notice, 10 * MINUTE_IN_SECONDS );
		wp_safe_redirect( wp_get_referer() ? wp_get_referer() : admin_url( 'edit.php' ) );
		exit;
	}
);

// The same two actions in the article editor's sidebar, with the last request.
add_action(
	'add_meta_boxes_post',
	function ( $post ) {
		if ( ! current_user_can( 'publish_posts' ) ) {
			return;
		}
		add_meta_box(
			'itv-production',
			'Production',
			function ( $post ) {
				$key    = 'itv_production_notice_' . get_current_user_id();
				$notice = get_transient( $key );
				if ( $notice ) {
					delete_transient( $key );
					printf( '<p style="color:%s"><strong>%s</strong></p>', $notice[0] ? '#00713a' : '#b32d2e', esc_html( $notice[1] ) );
				}
				if ( 'publish' === $post->post_status ) {
					printf(
						'<p><a class="button button-primary" href="%s" onclick="return confirm(%s)">Publish to production</a></p>',
						esc_url( itv_production_link( 'publish', $post->ID ) ),
						esc_attr( wp_json_encode( 'Ask GitHub to publish this article on production? You will approve it there.' ) )
					);
				} else {
					echo '<p>To publish on production, first publish the article here on staging and review it.</p>';
				}
				printf(
					'<p><a class="button" href="%s" onclick="return confirm(%s)">Unpublish from production</a></p>',
					esc_url( itv_production_link( 'unpublish', $post->ID ) ),
					esc_attr( wp_json_encode( 'Ask GitHub to take this article off production? You will approve it there.' ) )
				);
				$last = get_post_meta( $post->ID, '_itv_production_request', true );
				printf( '<p class="description">Last request: %s</p>', esc_html( $last ? $last : 'none' ) );
				echo '<p class="description">Requests wait for approval in GitHub: Actions › Publish or unpublish article. Save your changes first: these links leave the editor.</p>';
			},
			'post',
			'side',
			'high'
		);
	}
);

add_action(
	'admin_notices',
	function () {
		$key    = 'itv_production_notice_' . get_current_user_id();
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
