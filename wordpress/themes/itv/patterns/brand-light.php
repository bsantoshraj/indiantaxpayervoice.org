<?php
/**
 * Title: Brand (on dark)
 * Slug: itv/brand-light
 * Inserter: no
 */
?>
<!-- wp:html -->
<a class="itv-brand" href="<?php echo esc_url( home_url( '/' ) ); ?>" rel="home">
	<img src="<?php echo esc_url( get_stylesheet_directory_uri() . '/assets/logo-mark-light.svg' ); ?>" alt="" width="40" height="40">
	<span class="itv-brand__text">
		<span class="itv-brand__name">Indian Taxpayer <span>Voice</span></span>
		<span class="itv-brand__tagline"><?php echo esc_html( get_bloginfo( 'description' ) ); ?></span>
	</span>
</a>
<!-- /wp:html -->
