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
    [Color.PRIMARY]: Color.LIGHT,
    [Color.SECONDARY]: Color.LIGHT,
    [Color.SUCCESS]: Color.LIGHT,
    [Color.DANGER]: Color.LIGHT,
    [Color.WARNING]: Color.DARK,
    [Color.INFO]: Color.DARK,
    [Color.LIGHT]: Color.DARK,
    [Color.DARK]: Color.LIGHT,
    [Color.WHITE]: Color.DARK,
    [Color.BLACK]: Color.WHITE,
}
