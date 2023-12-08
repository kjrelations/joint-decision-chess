def default_themes(names = None):
	themes = [
		{
			"name": "Standard",
			"white_square": [255, 230, 155],
			"black_square": [140, 215, 230],
			"transparent_circles": [255, 180, 155, 160],
			"transparent_special_circles": [140, 95, 80, 160],
			"hover_outline_color_white": [255, 240, 200],
			"hover_outline_color_black": [200, 235, 245],
			"font_size": 36,
			"highlight_white": [255, 215, 105],
			"highlight_black": [75, 215, 230],
			"highlight_white_red": [255, 100, 70],
			"highlight_black_red": [150, 60, 40],
			"arrow_white": [235, 180, 50, 150],
			"arrow_black": [0, 100, 100, 150],
			"arrow_body_width": 20,
			"arrow_head_height": 35,
			"arrow_head_width": 48
		},
		{
			"name": "Dark Wooden",
			"white_square": [255, 240, 200],
			"black_square": [85, 75, 55],
			"transparent_circles": [255, 180, 155, 160],
			"transparent_special_circles": [140, 40, 5, 160],
			"hover_outline_color_white": [255, 250, 230],
			"hover_outline_color_black": [155, 135, 100],
			"font_size": 36,
			"highlight_white": [255, 220, 135],
			"highlight_black": [75, 55, 25],
			"highlight_white_red": [255, 100, 70],
			"highlight_black_red": [150, 60, 40],
			"arrow_white": [235, 180, 50, 150],
			"arrow_black": [135, 125, 100, 150],
			"arrow_body_width": 20,
			"arrow_head_height": 35,
			"arrow_head_width": 48
		},
		{
			"name": "Wooden",
			"white_square": [200, 175, 125],
			"black_square": [140, 100, 60],
			"transparent_circles": [255, 180, 155, 160],
			"transparent_special_circles": [140, 40, 5, 160],
			"hover_outline_color_white": [225, 210, 180],
			"hover_outline_color_black": [195, 155, 115],
			"font_size": 36,
			"highlight_white": [200, 155, 75],
			"highlight_black": [90, 60, 25],
			"highlight_white_red": [255, 100, 70],
			"highlight_black_red": [150, 60, 40],
			"arrow_white": [235, 180, 50, 150],
			"arrow_black": [135, 125, 100, 150],
			"arrow_body_width": 20,
			"arrow_head_height": 35,
			"arrow_head_width": 48
		},
		{
			"name": "Tournament",
			"white_square": [230, 240, 205],
			"black_square": [120, 150, 85],
			"transparent_circles": [255, 180, 155, 160],
			"transparent_special_circles": [140, 95, 80, 160],
			"hover_outline_color_white": [245, 250, 230],
			"hover_outline_color_black": [165, 185, 135],
			"font_size": 36,
			"highlight_white": [235, 235, 115],
			"highlight_black": [130, 150, 40],
			"highlight_white_red": [255, 100, 70],
			"highlight_black_red": [150, 60, 40],
			"arrow_white": [235, 180, 50, 150],
			"arrow_black": [190, 200, 95, 150],
			"arrow_body_width": 20,
			"arrow_head_height": 35,
			"arrow_head_width": 48
		},
		{
			"name": "Royal",
			"white_square": [255, 205, 105],
			"black_square": [110, 145, 190],
			"transparent_circles": [175, 125, 105, 160],
			"transparent_special_circles": [140, 40, 5, 160],
			"hover_outline_color_white": [255, 235, 185],
			"hover_outline_color_black": [160, 185, 215],
			"font_size": 36,
			"highlight_white": [255, 250, 105],
			"highlight_black": [35, 85, 150],
			"highlight_white_red": [255, 100, 70],
			"highlight_black_red": [150, 60, 40],
			"arrow_white": [255, 250, 105, 150],
			"arrow_black": [35, 85, 150, 150],
			"arrow_body_width": 20,
			"arrow_head_height": 35,
			"arrow_head_width": 48
		},
		{
			"name": "Adversary",
			"white_square": [255, 205, 105],
			"black_square": [250, 145, 105],
			"transparent_circles": [140, 215, 230, 160],
			"transparent_special_circles": [60, 120, 230, 160],
			"hover_outline_color_white": [255, 225, 170],
			"hover_outline_color_black": [250, 185, 160],
			"font_size": 36,
			"highlight_white": [255, 250, 105],
			"highlight_black": [170, 70, 40],
			"highlight_white_red": [75, 115, 195],
			"highlight_black_red": [15, 50, 135],
			"arrow_white": [255, 255, 255, 150],
			"arrow_black": [195, 120, 60, 150],
			"arrow_body_width": 20,
			"arrow_head_height": 35,
			"arrow_head_width": 48
		},
		{
			"name": "Regal",
			"white_square": [255, 205, 105],
			"black_square": [190, 50, 5],
			"transparent_circles": [255, 180, 155, 160],
			"transparent_special_circles": [140, 95, 80, 160],
			"hover_outline_color_white": [255, 225, 170],
			"hover_outline_color_black": [250, 105, 60],
			"font_size": 36,
			"highlight_white": [255, 250, 105],
			"highlight_black": [130, 35, 0],
			"highlight_white_red": [75, 115, 195],
			"highlight_black_red": [15, 50, 135],
			"arrow_white": [255, 255, 255, 150],
			"arrow_black": [70, 20, 0, 150],
			"arrow_body_width": 20,
			"arrow_head_height": 35,
			"arrow_head_width": 48
		},
		{
			"name": "Portal",
			"white_square": [255, 190, 100],
			"black_square": [40, 165, 215],
			"transparent_circles": [175, 125, 105, 160],
			"transparent_special_circles": [140, 40, 5, 160],
			"hover_outline_color_white": [255, 215, 160],
			"hover_outline_color_black": [135, 205, 235],
			"font_size": 36,
			"highlight_white": [250, 200, 40],
			"highlight_black": [25, 95, 155],
			"highlight_white_red": [255, 100, 70],
			"highlight_black_red": [150, 60, 40],
			"arrow_white": [230, 155, 55, 150],
			"arrow_black": [0, 100, 100, 150],
			"arrow_body_width": 20,
			"arrow_head_height": 35,
			"arrow_head_width": 48
		},
		{
			"name": "Bubblegum",
			"white_square": [250, 195, 175],
			"black_square": [90, 160, 215],
			"transparent_circles": [175, 125, 105, 160],
			"transparent_special_circles": [140, 40, 5, 160],
			"hover_outline_color_white": [255, 225, 215],
			"hover_outline_color_black": [155, 200, 230],
			"font_size": 36,
			"highlight_white": [240, 130, 90],
			"highlight_black": [30, 115, 180],
			"highlight_white_red": [255, 100, 70],
			"highlight_black_red": [150, 60, 40],
			"arrow_white": [250, 115, 70, 150],
			"arrow_black": [0, 100, 100, 150],
			"arrow_body_width": 20,
			"arrow_head_height": 35,
			"arrow_head_width": 48
		}
	]
	if names is None:
		ordered = themes
	else:
		ordered = [theme for theme in themes if theme['name'] in names]
	# TODO ? have function replace single quotes
	return [str(value) for value in ordered]