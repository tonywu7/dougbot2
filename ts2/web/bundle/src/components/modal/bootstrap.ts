export enum Color {
    PRIMARY = 'primary',
    SECONDARY = 'secondary',
    SUCCESS = 'success',
    DANGER = 'danger',
    WARNING = 'warning',
    INFO = 'info',
    LIGHT = 'light',
    DARK = 'dark',
    WHITE = 'white',
    BLACK = 'black',
}

export let COLOR_CONTRAST: Record<Color, Color> = {
    [Color.PRIMARY]: Color.WHITE,
    [Color.SECONDARY]: Color.WHITE,
    [Color.SUCCESS]: Color.WHITE,
    [Color.DANGER]: Color.WHITE,
    [Color.WARNING]: Color.BLACK,
    [Color.INFO]: Color.BLACK,
    [Color.LIGHT]: Color.BLACK,
    [Color.DARK]: Color.WHITE,
    [Color.WHITE]: Color.BLACK,
    [Color.BLACK]: Color.WHITE,
}
